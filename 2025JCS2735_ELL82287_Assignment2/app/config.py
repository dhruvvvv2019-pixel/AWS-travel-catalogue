import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")
DYNAMODB_TABLE = os.getenv(
    "DYNAMODB_TABLE",
    "ELL82287-TravelDestinations"
)
S3_BUCKET = os.getenv(
    "S3_BUCKET",
    "ell82287-travel-catalogue-images-2026"
)
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "")

APP_ENV = os.getenv("APP_ENV", "local")
