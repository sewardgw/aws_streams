import time
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


#Main function for get regions and run the query on the captured regions
def lambda_handler(event, context):
    request_id = event['RequestId']
    try:
        logger.info('RequestId {} - Received event to update firehose parameters for: {}'.format(request_id, event))
        if event['RequestType'] == 'Delete':
            logger.info('Nothing to do. Deleting stack for RequestId {}'.format(request_id))
            # sendResponse(event, context, SUCCESS, {})
            send(event, context, SUCCESS, {})
        else:
            stream_info = event['ResourceProperties']
            region = stream_info['region']
            logger.info('RequestId {} - Creating Firehose connector from Boto3 in region {}'.format(request_id, region))
            fh = boto3.client('firehose', region_name=region)

            firehose_name = stream_info['firehose_name']

            logger.info('RequestId {} - Retrieving stream descritption for Firehose {}'.format(request_id, firehose_name))
            stream_desc = fh.describe_delivery_stream(DeliveryStreamName=firehose_name)['DeliveryStreamDescription']
            stream_dest_id = stream_desc['Destinations'][0]['DestinationId']
            stream_version = stream_desc['VersionId']
            ext_dest = json.loads(stream_info['ext_dest_str'])

            logger.info('RequestId {} - Updating Firehose'.format(request_id))
            logger.info('RequestId {} - Firehose Name: {}'.format(request_id, firehose_name))
            logger.info('RequestId {} - Version: {}'.format(request_id, stream_version))
            logger.info('RequestId {} - DestinationId: {}'.format(request_id, stream_dest_id))
            logger.info('RequestId {} - External Destination Configurations: {}'.format(request_id, ext_dest))

            update_response = fh.update_destination(
                DeliveryStreamName=firehose_name,
                CurrentDeliveryStreamVersionId=stream_version,
                DestinationId=stream_dest_id,
                ExtendedS3DestinationUpdate=ext_dest
            )

            resp_metadata = update_response['ResponseMetadata']
            resp_code = resp_metadata['HTTPStatusCode']
            responseData = {}
            responseData['Data'] = resp_code

            if resp_code == 200:
                logger.info('RequestId {} - Update completed successfully.'.format(request_id))
                # sendResponse(event, context, SUCCESS, resp_metadata)
                send(event, context, SUCCESS, resp_metadata)
            else:
                logger.error('RequestId {} - Update failed: '.format(request_id, update_response))
                # sendResponse(event, context, FAILED, resp_metadata)
                send(event, context, FAILED, {})

    except Exception as e:
        logger.error('RequestId {} - Error: '.format(request_id, e))
        resp_error = {}
        resp_error['error'] = str(e)
        # sendResponse(event, context, FAILED, resp_error)
        send(event, context, FAILED, resp_error)
