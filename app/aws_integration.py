import boto3
from dotenv import load_dotenv
from os import getenv

load_dotenv()

def get_aws_connection():

    s3 = boto3.client(
        's3',
        aws_access_key_id=getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=getenv('AWS_REGION_NAME')
    )

    return s3

