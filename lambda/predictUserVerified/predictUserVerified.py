import io
import sys
import json
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

import boto3
import pandas as pd
import numpy as np


s3 = boto3.client('s3')
athena = boto3.client('athena', region_name='us-west-2')
sagemaker = boto3.client('runtime.sagemaker', region_name='us-west-2')
kinesis = boto3.client('kinesis', region_name='us-west-2')


QUERY_OUTPUT_BUCKET = 'aws-athena-query-results-652741540129-us-west-2'
ENDPOINT_NAME = 'DEMO-XGBoostEndpoint-2018-11-22-16-21-28'
OUTPUT_STREAM = 'pred_verified_users'


def parquet_object_to_df(bucket, obj):
    logger.info('Collecting object: {} from bucket: {}'.format(obj, bucket))
    bucket = boto3.resource('s3').Bucket(bucket)
    s3_obj = bucket.Object(obj)

    if obj.endswith('.parquet'):
        logger.info('Reading parquet object.')
        buffer = io.BytesIO()
        s3_obj.download_fileobj(buffer)
        logger.info('Object downloaded. Converting to Parquet.')
        df = pd.read_parquet(buffer)
        logger.info('Object converted to parquet.')
        return df
    elif obj.endswith('.gz'):
        logger.info('Reading compressed object.')
        stream_str = io.BytesIO(s3_obj.get()['Body'].read())
        logger.info('Object downloaded. Reading as JSON.')
        # TODO: Should be able to determine the type of data and handle here
        df = pd.read_json(stream_str, compression='gzip', lines=True)
    return df

def get_query_from_df(df):
    logger.info('Generating query string.')
    def _fix_name(name):
        return name.replace("'",'').replace('|','').replace('.', '').replace(',','').replace('/','').replace('-','').replace('~','')
    query = """
        SELECT
        name, count(*) num_tweets
        FROM dev_cf_data.bball_user
        WHERE name IN
            (SELECT *
            FROM ( VALUES {} ) AS t (name))
        GROUP BY name
    """.format(','.join([ "('{}')".format(_fix_name(n)) for n in df.name.unique() if all(ord(x) < 128 for x in n)]))
    logger.info('Query string generated:\n {}'.format(query))
    return query

def begin_query(query, database):
    logger.info('Starting to execute query on database: {}.'.format(database))
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': database
        },
        ResultConfiguration={
            'OutputLocation': 's3://' + QUERY_OUTPUT_BUCKET,
        }
    )
    query_exec_id = response['QueryExecutionId']
    logger.info('Query started. Output location: s3://{}/{}.csv'.format(QUERY_OUTPUT_BUCKET, query_exec_id))
    return query_exec_id

def wait_for_query(query_id):
    logger.info('Waiting for object to be created.')
    s3_waiter = s3.get_waiter('object_exists')
    s3_waiter.wait(Bucket=QUERY_OUTPUT_BUCKET,
                   Key=query_id + '.csv',
                   WaiterConfig={
                        'Delay': 1,
                        'MaxAttempts': 200
                   }
    )

def get_query_results(query_id):
    logger.info('Retrieving query results.')
    results = athena.get_query_results(
        QueryExecutionId=query_id,
        # NextToken='string',
        MaxResults=5
    )
    logger.info('Query results retrieved.')
    return results

def results_to_df(results):
    logger.info('Converting query results to DataFrame.')
    rows =  results['ResultSet']['Rows']
    header = [c['VarCharValue'] for c in rows[0]['Data']]
    data = [[n['VarCharValue'] for n in v['Data']] for v in rows[1:]]
    df = pd.DataFrame(data, columns=header)
    logger.info('Query results successfully converted to DataFrame.')
    return df

def create_features(orig_df, results_df):
    logger.info('Creating final features for scoring.')
    def _location_is_major_city(row):
        location = (row['location'] or 'n/a').lower()
        major_cities = ['new york', 'chicago', 'miami', 'los angeles', 'boston', 'charlotte', 'dallas', 'houston']
        return int(location in major_cities)
    def _name_has_multiple_spaces(row):
        name = row['name']
        if ' ' in name:
            return len(name.split(' ')) - 1
        else:
            return 0
    orig_df['loc_is_major_city'] = orig_df.apply(_location_is_major_city, axis=1)
    orig_df['num_spacs_in_name'] = orig_df.apply(_name_has_multiple_spaces, axis=1)
    features = orig_df.merge(results_df, on='name', how='left').fillna(0)
    features = features[['user_age_at_post', 'loc_is_major_city', 'num_spacs_in_name', 'num_tweets']]
    return features

# Function to convert matrix to csv format for predictions
def np2csv(arr):
    return '\n'.join([','.join([str(s) for s in y ]) for y in arr])

# Function to generate prediction through sample data
def do_predict(data, endpoint_name, content_type):
    payload = np2csv(data)
    response = sagemaker.invoke_endpoint(EndpointName=endpoint_name,
                                         ContentType=content_type,
                                         Body=payload)
    result = response['Body'].read()
    result = result.decode("utf-8")
    result = result.split(',')
    preds = [float((num)) for num in result]
    return preds

# Function to iterate through a larger data set and generate batch predictions
def batch_predict(data, batch_size, endpoint_name, content_type):
    logger.info('Predicting score for records.')
    items = len(data)
    arrs = []
    for offset in range(0, items, batch_size):
        if offset+batch_size < items:
            datav = data[offset:(offset+batch_size),:]
            results = do_predict(datav, endpoint_name, content_type)
            arrs.extend(results)
        else:
            datav = data[offset:items,:]
            arrs.extend(do_predict(datav, endpoint_name, content_type))
    logger.info('Predictions complete.')
    return(arrs)

def send_high_prob_to_stream(df, prob_col='pred', prob_thresh=.1):
    logger.info('Sending predictions to {} Kinesis stream.'.format(OUTPUT_STREAM))
    high_probs = df[df[prob_col] >= prob_thresh]
    print(len(high_probs))
    rcds_sent = 0
    for n in range(len(high_probs)):
        try:
            kinesis.put_record(
                    StreamName=OUTPUT_STREAM,
                    Data=high_probs.iloc[n].to_json() + '\n',
                    PartitionKey='location'
            )
            rcds_sent += 1
        except Exception as e:
            logger.error('Error writing to stream: {}, error: {}'.format(OUTPUT_STREAM, str(e)))
    logger.info('Sent {} records to stream {}'.format(rcds_sent, OUTPUT_STREAM))
    print('Sent {} records to stream {}'.format(rcds_sent, OUTPUT_STREAM))

def lambda_handler(event, context):
    """
    Currently reads from an SNS event.
    """
    logger.info('Received event to score new predictions:\n {}'.format(event))
    for sns_event in event['Records']:
        for i, rcd in  enumerate(json.loads(sns_event['Sns']['Message'])['Records']):
            logger.info('Beginning to process record {}'.format(i + 1))
            bucket = rcd['s3']['bucket']['name']
            obj = rcd['s3']['object']['key']
            database = bucket.replace('-', '_')
            df = parquet_object_to_df(bucket, obj)
            query = get_query_from_df(df)
            query_exec_id = begin_query(query, database)
            wait_for_query(query_exec_id)
            query_results = get_query_results(query_exec_id)
            results_df = results_to_df(query_results)
            features = create_features(df, results_df)
            preds = batch_predict(features.values, 1000, ENDPOINT_NAME, 'text/csv')
            df['pred'] = preds
            send_high_prob_to_stream(df)
