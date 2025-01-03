from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from botocore.exceptions import ClientError
import boto3
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
ROLE_NAME = os.getenv("ROLE_NAME")

# Constants for EC2 Metadata Service
METADATA_URL = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
TOKEN_URL = "http://169.254.169.254/latest/api/token"


def get_aws_credentials():
    """Fetch AWS temporary credentials from EC2 instance metadata."""
    try:
        # Get the metadata token
        token_response = requests.put(
            TOKEN_URL, headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"})
        token = token_response.text

        # Fetch credentials for the IAM role
        credentials_response = requests.get(
            f"{METADATA_URL}{ROLE_NAME}",
            headers={"X-aws-ec2-metadata-token": token}
        )
        credentials = credentials_response.json()

        return {
            "aws_access_key_id": credentials["AccessKeyId"],
            "aws_secret_access_key": credentials["SecretAccessKey"],
            "aws_session_token": credentials["Token"]
        }
    except Exception as e:
        raise RuntimeError(f"Failed to fetch AWS credentials: {str(e)}")


# Fetch credentials
aws_credentials = get_aws_credentials()

# Initialize S3 client with temporary credentials
s3_client = boto3.client(
    "s3",
    aws_access_key_id=aws_credentials["aws_access_key_id"],
    aws_secret_access_key=aws_credentials["aws_secret_access_key"],
    aws_session_token=aws_credentials["aws_session_token"]
)
# Initialize DynamoDB client
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=aws_credentials["aws_access_key_id"],
    aws_secret_access_key=aws_credentials["aws_secret_access_key"],
    aws_session_token=aws_credentials.get("aws_session_token"),
    region_name="us-east-1"
)
# Connect to DynamoDB Table
TABLE_NAME = "Messages"
messages_table = dynamodb.Table(TABLE_NAME)

# Define Message schema


class Message(BaseModel):
    content: str


# Initialize FastAPI app
app = FastAPI()


@app.get("/health")
async def health_check():
    """Health check endpoint to verify the server is running."""
    return {"status": "ok"}


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Uploads a file to the S3 bucket."""
    try:
        # Check file type
        if not file.content_type.startswith("text/"):
            raise HTTPException(
                status_code=400, detail="Only text files are allowed.")

        # Upload file to S3
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, file.filename)
        return {"message": f"File '{file.filename}' uploaded successfully."}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/read/{file_name}")
async def read_file(file_name: str):
    """Reads a file from the S3 bucket."""
    try:
        # Download file content
        response = s3_client.get_object(
            Bucket=S3_BUCKET_NAME, Key=file_name)
        content = response["Body"].read().decode("utf-8")
        return {"file_name": file_name, "content": content}
    except ClientError as e:
        if e.response['Error']['Code'] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found.")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/message/")
async def create_message(message: Message):
    """Endpoint to create a new message."""
    try:
        message_id = str(uuid4())  # Generate a unique ID for the message
        item = {
            "message_id": message_id,
            "content": message.content
        }
        messages_table.put_item(Item=item)  # Save to DynamoDB
        return {"message_id": message_id, "content": message.content}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving message: {str(e)}")


@app.get("/messages/")
async def get_messages():
    """Endpoint to retrieve all messages."""
    try:
        response = messages_table.scan()  # Fetch all items from DynamoDB
        items = response.get("Items", [])
        return {"messages": items}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving messages: {str(e)}")
