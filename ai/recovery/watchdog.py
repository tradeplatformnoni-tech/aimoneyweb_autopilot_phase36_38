import subprocess,time,os
def ensure_process(cmd:str, name="subsystem"):
    while True:
        proc=subprocess.Popen(cmd,shell=True)
        proc.wait()
        print(f"🔁 {name} crashed — restarting in 5s")
        time.sleep(5)
