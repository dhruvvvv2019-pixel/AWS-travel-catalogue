import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from app.config import (
    AWS_REGION,
    DYNAMODB_TABLE,
    S3_BUCKET,
    SNS_TOPIC_ARN,
)


# AWS clients/resources.
# When running on EC2, boto3 automatically uses the EC2 IAM role.
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

from botocore.config import Config

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    config=Config(signature_version="s3v4"),
)
sns_client = boto3.client("sns", region_name=AWS_REGION)


def create_destination(
    name,
    country,
    city,
    category,
    description,
    budget,
    image_file=None,
):
    """Create a destination in DynamoDB and optionally upload its image to S3."""

    destination_id = str(uuid.uuid4())
    image_key = ""

    # Upload image to S3 if one was provided.
    if image_file and image_file.filename:
        extension = image_file.filename.rsplit(".", 1)[-1].lower()
        image_key = f"{destination_id}.{extension}"

        s3_client.upload_fileobj(
            image_file,
            S3_BUCKET,
            image_key,
            ExtraArgs={
                "ContentType": image_file.content_type
                or "application/octet-stream"
            },
        )

    destination = {
        "destination_id": destination_id,
        "name": name,
        "country": country,
        "city": city,
        "category": category,
        "description": description,
        "budget": int(budget),
        "image_key": image_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    table.put_item(Item=destination)

    # Notify subscribers after successful insertion.
    if SNS_TOPIC_ARN:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="New Travel Destination Added",
            Message=(
                "A new travel destination was added.\n\n"
                f"Destination: {name}\n"
                f"Country: {country}\n"
                f"City: {city}\n"
                f"Category: {category}\n"
                f"Budget: ₹{int(budget):,}"
            ),
        )

    return destination


def list_destinations():
    """Return all destinations from DynamoDB."""

    response = table.scan()
    items = response.get("Items", [])

    # Handle DynamoDB pagination.
    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    # Newest destinations first.
    items.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )

    return items


def get_destination(destination_id):
    """Return one destination by ID."""

    response = table.get_item(
        Key={"destination_id": destination_id}
    )

    return response.get("Item")


def get_image(image_key):
    if not image_key:
        return None, None

    response = s3_client.get_object(
        Bucket=S3_BUCKET,
        Key=image_key,
    )

    return (
        response["Body"].read(),
        response.get("ContentType", "application/octet-stream"),
    )

def delete_destination(destination_id):
    """Delete a destination and its associated S3 image."""

    destination = get_destination(destination_id)

    if not destination:
        return False

    image_key = destination.get("image_key")

    table.delete_item(
        Key={"destination_id": destination_id}
    )

    if image_key:
        try:
            s3_client.delete_object(
                Bucket=S3_BUCKET,
                Key=image_key,
            )
        except ClientError:
            pass

    return True
