# This function takes in an s3 event and then ensures that the partition has been added
# to the Glue catalog so that Athena can always query the most current data

import boto3
import json
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    athena = boto3.client('athena')
    logger.info(event)
    for sns_event in event['Records']:
        for rcd in json.loads(sns_event['Sns']['Message'])['Records']:
            bucket = rcd['s3']['bucket']['name']
            # The Glue database name MUST match the bucket name except replacing dashes with underscores
            database_name = bucket.replace('-','_')
            object = rcd['s3']['object']['key']
            # The Glue table name MUST match the first obect key except replacing dashes with underscores
            object_keys = object.split('/')
            table_key = object_keys[0]
            table_name = table_key.replace('-', '_')
            year = object_keys[-5]
            month = object_keys[-4]
            day = object_keys[-3]
            hour = object_keys[-2]

            query_dict = {
                'year': year,
                'month': month,
                'day': day,
                'hour': hour,
                'database_name': database_name,
                'table_name': table_name,
                'table_key': table_key,
                's3_bucket': bucket,
            }

            query = ''' ALTER TABLE {database_name}.{table_name}
                        add if not exists partition (year="{year}", month="{month}", day="{day}", hour="{hour}")
                        location "s3://{s3_bucket}/{table_key}/{year}/{month}/{day}/{hour}/";
            '''.format(**query_dict)
            logger.info('Executing query:')
            logger.info(query)
            athena.start_query_execution(
                QueryString=query,
                ResultConfiguration={
                    'OutputLocation': "s3://aws-athena-query-results-652741540129-us-west-2"
                }
            )
            athena.start_query_execution(
                QueryString="msck repair table {database_name}.{table_name}".format(**query_dict),
                ResultConfiguration={
                    'OutputLocation': "s3://aws-athena-query-results-652741540129-us-west-2"
                }
            )
