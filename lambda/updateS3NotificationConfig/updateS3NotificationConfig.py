# This function takes in an S3 bucket and a JSON representing a new Lambda notification configurtation
# and updates the S3 notification delivery configurations. This should only be called after executing
# a stack creation/update through CFT.

import json
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

import boto3
from botocore.vendored import requests

SUCCESS = 'SUCCESS'
FAILED = 'FAILED'

def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False):
    responseUrl = event['ResponseURL']
    logger.info('RequestId {} - preparting to send response to {}'.format(event['RequestId'], responseUrl) )
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'See the details in CloudWatch Log Stream: ' + str(context.log_stream_name)
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = responseData

    json_responseBody = json.dumps(responseBody)
    logger.info('RequestId {} - response content: {}'.format(event['RequestId'], json_responseBody) )

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        logger.info('RequestId {} - received status code: {}'.format(event['RequestId'], response.reason) )
    except Exception as e:
        logger.info('RequestId {} - received exception: {}'.format(event['RequestId'], e) )


def lambda_handler(event, context):
    request_id = event['RequestId']
    try:
        logger.info('RequestId {} - Received event to update S3 Notification Configurations for: {}'.format(request_id, event))
        if event['RequestType'] == 'Delete':
            logger.info('Nothing to do. Deleting stack for RequestId {}'.format(request_id))
            send(event, context, SUCCESS, {})
        else:
            s3 = boto3.client('s3')

            new_cofigs = event['ResourceProperties']
            bucket = new_cofigs['bucket']
            notification_configs = json.loads(new_cofigs['notification_configs'])

            logger.info('RequestId {} - Updating notifications for bucket: {}'.format(request_id, bucket))
            logger.info('RequestId {} - New notification configs: \n{}'.format(request_id, notification_configs))

            response = s3.put_bucket_notification_configuration(
                Bucket=bucket,
                NotificationConfiguration=notification_configs
            )

            resp_metadata = response['ResponseMetadata']
            resp_code = resp_metadata['HTTPStatusCode']
            responseData = {}
            responseData['Data'] = resp_code

            if resp_code == 200:
                logger.info('RequestId {} - Update completed successfully.'.format(request_id))
                send(event, context, SUCCESS, resp_metadata)
            else:
                logger.error('RequestId {} - Update failed: '.format(request_id, update_response))
                send(event, context, FAILED, {})

    except Exception as e:
        logger.error('RequestId {} - Error: '.format(request_id, e))
        resp_error = {}
        resp_error['error'] = str(e)
        # sendResponse(event, context, FAILED, resp_error)
        send(event, context, FAILED, resp_error)
