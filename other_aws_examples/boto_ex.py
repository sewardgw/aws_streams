import boto3
import sys
import json
import pandas as pd
import numpy as np
glue = boto3.client(
            'glue',
            region_name='us-west-2'
        )

tables = glue.get_tables(DatabaseName='cf_data')
raw = tables['TableList']
for r in raw:
    print(json.dumps(r, indent=4, default=str))

fh = boto3.client(
            'firehose',
            region_name='us-west-2'
        )

stream_desc = fh.describe_delivery_stream(DeliveryStreamName="pl-deploy-KinesisToS3FirehoseResource-dev")
print(json.dumps(stream_desc, indent=4, default=str))


streams = fh.list_delivery_streams()
print(json.dumps(streams, indent=4, default=str))


dest_str = '''
{
    "RoleARN": "arn:aws:iam::652741540129:role/ns2-KinesisFireHoseToS3Role-dev",
    "Prefix": "/bball-user/",
    "BufferingHints": {
        "IntervalInSeconds": 60,
        "SizeInMBs": 1
    },
    "EncryptionConfiguration": {
        "NoEncryptionConfig": "NoEncryption"
    },
    "CompressionFormat": "UNCOMPRESSED",
    "CloudWatchLoggingOptions": {
        "Enabled": true,
        "LogStreamName": "S3Delivery",
        "LogGroupName": "/aws/kinesisfirehose/stream1"
    },
    "BucketARN": "arn:aws:s3:::cf-data"
}
'''

ext_dest_str = '''{
    "DataFormatConversionConfiguration": {
        "OutputFormatConfiguration": {
            "Serializer": {
                "ParquetSerDe": {}
            }
        },
        "SchemaConfiguration": {
            "RoleARN": "arn:aws:iam::652741540129:role/ns2-KinesisFireHoseToS3Role-dev",
            "TableName": "bball_user",
            "Region": "us-west-2",
            "DatabaseName": "cf-data",
            "VersionId": "LATEST"
        },
        "Enabled": true,
        "InputFormatConfiguration": {
            "Deserializer": {
                "OpenXJsonSerDe": {}
            }
        }
    },
    "RoleARN": "arn:aws:iam::652741540129:role/ns2-KinesisFireHoseToS3Role-dev",
    "Prefix": "bball-user/",
    "BufferingHints": {
        "IntervalInSeconds": 60,
        "SizeInMBs": 128
    },
    "EncryptionConfiguration": {
        "NoEncryptionConfig": "NoEncryption"
    },
    "CompressionFormat": "UNCOMPRESSED",
    "S3BackupMode": "Enabled",
    "CloudWatchLoggingOptions": {
        "Enabled": true,
        "LogStreamName": "S3Delivery",
        "LogGroupName": "/aws/kinesisfirehose/bball-user"
    },
    "BucketARN": "arn:aws:s3:::cf-data",
    "ProcessingConfiguration": {
        "Enabled": false,
        "Processors": []
    },
    "S3BackupMode": "Enabled",
    "S3BackupUpdate": {
        "RoleARN": "arn:aws:iam::652741540129:role/ns2-KinesisFireHoseToS3Role-dev",
        "BucketARN": "arn:aws:s3:::cf-data",
        "Prefix": "raw/",
        "BufferingHints": {
            "SizeInMBs": 123,
            "IntervalInSeconds": 123
        },
        "CompressionFormat": "GZIP",
        "EncryptionConfiguration": {
            "NoEncryptionConfig": "NoEncryption"
        },
        "CloudWatchLoggingOptions": {
            "Enabled": false
        }
    }
}'''

dest = json.loads(dest_str)
ext_dest = json.loads(ext_dest_str)

fh.update_destination(
    DeliveryStreamName='ns2-KinesisToS3FirehoseResource-dev',
    CurrentDeliveryStreamVersionId='1',
    DestinationId='destinationId-000000000001',
    # S3DestinationUpdate=dest,
    ExtendedS3DestinationUpdate=ext_dest
)

fh.update_destination(
    DeliveryStreamName='ns2-KinesisToS3FirehoseResource-dev',
    CurrentDeliveryStreamVersionId='1',
    DestinationId='dsid-1',
    S3DestinationUpdate=dest,
    # ExtendedS3DestinationUpdate=ext_dest
)

a = glue.get_partitions(DatabaseName='cf_data', TableName='bball_user')



s3 = boto3.client(
            's3'
        )


response = s3.put_bucket_notification_configuration(
    Bucket='cf-data',
    NotificationConfiguration={
        'LambdaFunctionConfigurations': [
            {
                'Id': 'string',
                'LambdaFunctionArn': 'arn:aws:lambda:us-west-2:652741540129:function:core-data-common-UpdatePartitionsLambdaFunction-dev',
                'Events': ['s3:ObjectCreated:*'],
            },
        ]
    }
)

s3.get_bucket_notification_configuration(
    Bucket='cf-data'
)


sm = boto3.client('sagemaker-runtime',
                  region_name='us-west-2'
)
custom_attributes = "custom_attribute_string"  # An example of a trace ID.
endpoint_name = "DEMO-XGBoostEndpoint-2018-11-22-16-21-28"                                       # Your endpoint name.
content_type = "text/csv"                                        # The MIME type of the input data in the request body.
accept = "text/csv"                                              # The desired MIME type of the inference in the response.
payload = "3000,1,2,10"

response = sm.invoke_endpoint(
    EndpointName=endpoint_name,
    CustomAttributes=custom_attributes,
    ContentType=content_type,
    Accept=accept,
    Body=payload
    )
resp_body = response['Body']
pred = float(resp_body.read())
print(response['CustomAttributes'])



"""
Athena query to get feature calculations
"""
s3 = boto3.client('s3'
)


athena = boto3.client('athena',
                  region_name='us-west-2')
)

BUCKET = 'aws-athena-query-results-652741540129-us-west-2'
OBJ_BUCKET = 'dev-cf-data'
OBJECT_KEY = 'bball-user/2018/11/22/14/pl-deploy-KinesisToS3FirehoseResource-dev-2-2018-11-22-14-16-07-83683207-e068-4410-b622-c5198189c13f.parquet'

bucket = boto3.resource('s3', aws_access_key_id='AKIAJR2EUO62XEZRJ27Q', aws_secret_access_key='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').Bucket(OBJ_BUCKET)
obj = bucket.Object(OBJECT_KEY)

import io
buffer = io.BytesIO()
obj.download_fileobj(buffer)
df = pd.read_parquet(buffer)

df.head()


query1 = """
SELECT
name, count(*) num_tweets
FROM dev_cf_data.bball_user
WHERE name IN
    (SELECT *
    FROM ( VALUES ('Charley Rubey'), ('NBA News Now') ) AS t (name))
GROUP BY name
"""
print(query1)

n=999999
query = """
SELECT
name, count(*) num_tweets
FROM dev_cf_data.bball_user
WHERE name IN
    (SELECT *
    FROM ( VALUES {} ) AS t (name))
GROUP BY name
""".format(','.join(["('{}')".format(n.replace("'",'').replace('|','').replace('.', '').replace(',','').replace('/','').replace('-','').replace('~','')) for n in df.name.unique()[:n] if all(ord(x) < 128 for x in n)]))
print(query)

response = athena.start_query_execution(
    QueryString=query,
    QueryExecutionContext={
        'Database': 'dev_cf_data'
    },
    ResultConfiguration={
        'OutputLocation': 's3://' + BUCKET,
    }
)

query_exec_id = response['QueryExecutionId']
query_exec_id

s3_waiter = s3.get_waiter('object_exists')
a = s3_waiter.wait(Bucket=BUCKET,
               Key=query_exec_id + '.csv',
               WaiterConfig={
                'Delay': 1,
                'MaxAttempts': 200
              }
)

results = athena.get_query_results(
    QueryExecutionId=query_exec_id,
    # NextToken='string',
    MaxResults=1000
)

rows =  results['ResultSet']['Rows']
rows
header = [c['VarCharValue'] for c in rows[0]['Data']]
header
data = [[n['VarCharValue'] for n in v['Data']] for v in rows[1:]]
data = pd.DataFrame(data, columns=header)

def location_is_major_city(row):
    location = (row['location'] or 'n/a').lower()
    major_cities = ['new york', 'chicago', 'miami', 'los angeles', 'boston', 'charlotte', 'dallas', 'houston']
    return int(location in major_cities)

def name_has_multiple_spaces(row):
    name = row['name']
    if ' ' in name:
        return len(name.split(' ')) - 1
    else:
        return 0

df['loc_is_major_city'] = df.apply(location_is_major_city, axis=1)
df['num_spacs_in_name'] = df.apply(name_has_multiple_spaces, axis=1)

df2 = df.merge(data, on='name', how='left').fillna(0)
final_table = df2[['user_age_at_post', 'loc_is_major_city', 'num_spacs_in_name', 'num_tweets']]


runtime= boto3.client('runtime.sagemaker', region_name='us-west-2')

# Simple function to create a csv from our numpy array

def np2csv(arr):
    return '\n'.join([','.join([str(s) for s in y ]) for y in arr])
    # return '\n'.join([','.join([str(x) for x in y] for y in arr)])
    # csv = io.BytesIO()
    # np.savetxt(csv, arr, delimiter=',', fmt='%s')
    # return csv.getvalue().decode().rstrip()

# Function to generate prediction through sample data
def do_predict(data, endpoint_name, content_type):
    payload = np2csv(data)
    response = runtime.invoke_endpoint(EndpointName=endpoint_name,
                                   ContentType=content_type,
                                   Body=payload)
    result = response['Body'].read()
    result = result.decode("utf-8")
    result = result.split(',')
    preds = [float((num)) for num in result]
    return preds

# Function to iterate through a larger data set and generate batch predictions
def batch_predict(data, batch_size, endpoint_name, content_type):
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
        sys.stdout.write('.')
    return(arrs)

endpoint_name = 'DEMO-XGBoostEndpoint-2018-11-22-16-21-28'
results = batch_predict(final_table.values, 1000, endpoint_name, 'text/csv')

final_table.values
'\n'.join([','.join([str(s) for s in y ]) for y in final_table.values])
','.join([str(s) for s in final_table.as_matrix()[0]])

model_resp = runtime.invoke_endpoint(EndpointName=endpoint_name,
                               ContentType='text/csv',
                               Body=','.join([str(s) for s in final_table.as_matrix()[0]]))

resp_body = model_resp['Body']
pred = float(resp_body.read())
