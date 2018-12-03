
import time
import boto3

__STREAM_NAME__ = 'dog_stream'
__REGION__ = 'us-west-2'
__NUM_SHARDS__ = 3

class KinesisBasketballStreamer(object):
    def __init__(self):
        self.client = boto3.client(
            'kinesis',
            region_name='us-west-2',
            # Hard coded strings as credentials, not recommended.
            aws_access_key_id='AKIAJELMQ3JQZM2D63SQ',
            aws_secret_access_key='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'
        )
        self.stream_msgs_sent = {}

    def get_stream_status(self, stream_name):
        return self.client.describe_stream(StreamName=stream_name)['StreamDescription']['StreamStatus']

    def wait_for_stream(stream_name):
        SLEEP_TIME_SECONDS = 3
        status = self.get_stream_status(stream_name)
        while status != 'ACTIVE':
            print('{stream_name} has status: {status}, sleeping for {secs} seconds'.format(
                    stream_name = stream_name,
                    status      = status,
                    secs        = SLEEP_TIME_SECONDS))
            time.sleep(SLEEP_TIME_SECONDS) # sleep for 3 seconds
            status = self.get_stream_status(stream_name)
        print('{} is active.'.format(stream_name))

    def is_stream_active(self, stream_name):
        return self.get_stream_status(stream_name) == 'ACTIVE'

    def check_or_create_stream(self, stream_name):
        try:
            if self.is_stream_active(stream_name):
                pass
            else:
                print('Stream does not exist')
        except:
            pass
            # self.client.create_stream(StreamName=stream_name, ShardCount=__NUM_SHARDS__)
            # while not self.is_stream_active(stream_name):
            #     print('Stream not yet active. Sleeping for 5 seconds.')
            #     time.sleep(5)
            # print('Stream active.')

    def msg_sent_to_stream(self, stream_name):
        if stream_name not in self.stream_msgs_sent.keys():
            self.stream_msgs_sent[stream_name] = 0
        self.stream_msgs_sent[stream_name] += 1

    def send_msg_to_stream(self, stream_name, msg):
        try:
            if stream_name not in self.stream_msgs_sent.keys():
                print('checking status')
                # The line below will fail if the stream is not already created
                # print(self.get_stream_status(stream_name))
                self.check_or_create_stream(stream_name)

            self.client.put_record(
                    StreamName=stream_name,
                    Data=msg,
                    PartitionKey='partition1'
            )
            self.msg_sent_to_stream(stream_name)

        except Exception as e:
            print(e)
