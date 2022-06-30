import json
import boto3

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_xray_sdk.core import patch_all

# https://awslabs.github.io/aws-lambda-powertools-python/#features
tracer = Tracer()
logger = Logger()
metrics = Metrics()

# apply the XRay handler to all clients.
patch_all()

KvsClient = boto3.client('kinesisvideo')


@metrics.log_metrics(capture_cold_start_metric=True)
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    logger.info('## Inside handler, woho')

    stream_urls = []

    streams = KvsClient.list_streams(
        StreamNameCondition={
            'ComparisonOperator': 'BEGINS_WITH',
            'ComparisonValue': 'hassela'
        }
    )

    for stream in streams['StreamInfoList']:
        # Get the stream endpoints
        try:
            endpoint = KvsClient.get_data_endpoint(
                APIName="GET_HLS_STREAMING_SESSION_URL",
                StreamName=stream['StreamName']
            )['DataEndpoint']
        except:
            logger.error('Could not get kvs endpoint')
            break

        logger.info(endpoint)

        # initiate new archive client with the relevant endpoint
        KvsArchiveClient = boto3.client(
            'kinesis-video-archived-media', endpoint_url=endpoint)

        # Get HLS url
        try:
            url = KvsArchiveClient.get_hls_streaming_session_url(
                StreamName=stream['StreamName'],
                PlaybackMode="LIVE"
            )['HLSStreamingSessionURL']
        except:
            logger.error('Could not get HLS stream URL')
            break

        stream_urls.append(url)

        logger.info(stream_urls)

    body = {
        "message": 'ok',
        "streams": stream_urls
    }

    return {
        "statusCode": 200,
        "body": json.dumps(body),
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*'
        },
    }
