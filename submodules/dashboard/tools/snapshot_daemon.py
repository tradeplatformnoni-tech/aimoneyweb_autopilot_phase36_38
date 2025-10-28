"""
Simulated snapshot writer.  Appends equity history to runtime/snapshots.jsonl.
"""
import time, json, datetime, random, pathlib
RUNTIME=pathlib.Path("runtime"); FILE=RUNTIME/"snapshots.jsonl"
def loop():
    while True:
        eq=100000+random.uniform(-500,500)
        snap={"ts":datetime.datetime.utcnow().isoformat(),"equity":eq}
        FILE.open("a").write(json.dumps(snap)+"\n")
        time.sleep(300)
if __name__=="__main__": loop()
