from collections import namedtuple
import json

import pytest

from app import updateStreamExtendedDestination


@pytest.fixture()
def event():
    """ A sample Event"""

    return '''{"DataFormatConversionConfiguration": {
                 "OutputFormatConfiguration": {
                     "Serializer": {
                         "ParquetSerDe": {}
                     }
                 },
                 "SchemaConfiguration": {
                     "RoleARN": "${KinesisFireHoseToS3Role.Arn}",
                     "TableName": "${GlueTableName}",
                     "Region": "${Region}",
                     "DatabaseName": "${OutputDatabaseName}",
                     "VersionId": "LATEST"
                 },
                 "Enabled": true,
                 "InputFormatConfiguration": {
                     "Deserializer": {
                         "OpenXJsonSerDe": {}
                     }
                 }
                },
                "RoleARN": "${KinesisFireHoseToS3Role.Arn}",
                "Prefix": "${S3BucketKeyPrefix}/",
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
                 "LogGroupName": "/aws/kinesisfirehose/${S3BucketKeyPrefix}"
                },
                "BucketARN": "${DeliveryBucketArn}",
                "ProcessingConfiguration": {
                 "Enabled": false,
                 "Processors": []
                },
                "S3BackupMode": "Enabled",
                "S3BackupUpdate": {
                 "RoleARN": "${KinesisFireHoseToS3Role.Arn}",
                 "BucketARN": "${DeliveryBucketArn}",
                 "Prefix": "${S3BucketKeyPrefix}-raw/",
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


def test_lambda_handler(event):
    assert 'DataFormatConversionConfiguration' in json.loads(event).keys()
