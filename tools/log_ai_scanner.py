import re

def scan_log(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    errors = [line for line in lines if re.search(r'(Traceback|ERROR|Exception|KeyError|ValueError)', line)]
    if errors:
        print("❗ AI Scanner detected issues:")
        for err in errors[-5:]:
            print("🧠", err.strip())
    else:
        print("✅ No major errors detected.")

if __name__ == "__main__":
    scan_log("logs/backend.log")
