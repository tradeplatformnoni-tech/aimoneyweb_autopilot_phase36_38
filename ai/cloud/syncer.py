import boto3,os,time
from dotenv import load_dotenv; load_dotenv()
BUCKET=os.getenv("AWS_BUCKET","aimoneyweb-models")
REGION=os.getenv("AWS_REGION","us-east-1")
def upload_model(path="models/deep_rl_model.pt"):
    try:
        s3=boto3.client("s3",region_name=REGION)
        key=f"{time.strftime('%Y%m%d_%H%M%S')}_deep_rl_model.pt"
        s3.upload_file(path,BUCKET,key)
        print(f"✅ Uploaded model to s3://{BUCKET}/{key}")
        return True
    except Exception as e: print("⚠️ S3 upload failed:",e); return False
