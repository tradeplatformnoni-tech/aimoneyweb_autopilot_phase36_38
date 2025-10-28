import boto3, os, json, time
from dotenv import load_dotenv; load_dotenv()
BUCKET=os.getenv("AWS_BUCKET","aimoneyweb-sync")
REGION=os.getenv("AWS_REGION","us-east-1")

def push_state(state:dict):
    try:
        s3=boto3.client("s3",region_name=REGION)
        key=f"state_{time.strftime('%Y%m%d_%H%M%S')}.json"
        s3.put_object(Body=json.dumps(state),Bucket=BUCKET,Key=key)
        print(f"☁️ Cloud sync → s3://{BUCKET}/{key}")
    except Exception as e: print("⚠️ Cloud sync failed:",e)
