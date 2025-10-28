import os, time, boto3, glob
from dotenv import load_dotenv; load_dotenv()

BUCKET = os.getenv("S3_BUCKET")
def _client():
    if not BUCKET: return None
    return boto3.client("s3")

def upload_logs():
    c=_client()
    if not c: return "S3 not configured"
    sent=0
    for path in glob.glob("logs/*"):
        key=os.path.basename(path)
        try: c.upload_file(path, BUCKET, f"logs/{key}"); sent+=1
        except Exception as e: print("S3 err:",e)
    return f"uploaded:{sent}"

def backup_db():
    c=_client()
    if not c or not os.path.exists("db/trades.db"): return "no db or s3"
    key=f"db/trades_{int(time.time())}.sqlite"
    try: c.upload_file("db/trades.db", BUCKET, key); return key
    except Exception as e: return f"db upload err:{e}"

if __name__=="__main__":
    print(upload_logs()); print(backup_db())
