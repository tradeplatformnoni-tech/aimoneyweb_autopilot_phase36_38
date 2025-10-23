#!/usr/bin/env python3
import sys
import requests

def send_alert(message):
    # Replace with your real Pushover credentials
    user_key = "u56o3pt5bjrdaa81gpzetbyzz4dhyh"
    token = "aqb4vmo2gs73vfh6o4z9hx8pz8n713"

    payload = {
        "token": token,
        "user": user_key,
        "message": message
    }

    r = requests.post("https://api.pushover.net/1/messages.json", data=payload)
    print("📲 Alert sent!" if r.status_code == 200 else "❗ Alert failed.")


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "🧠 NeoLight Alert"
    send_alert(msg)
