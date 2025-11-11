# server.py - Flask endpoint to receive SOS and send SMS via Twilio
from flask import Flask, request, jsonify
from twilio.rest import Client
import os
import time

app = Flask(__name__)

# Twilio config (set as environment vars or replace)
TWILIO_SID = os.environ.get("TWILIO_SID") or "ACxxxxxxxx"
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN") or "your_auth_token"
TWILIO_FROM = os.environ.get("TWILIO_FROM") or "+1XXXXXXXXXX"

# Registered numbers: replace with real numbers
REGISTERED_NUMBERS = ["+91YYYYYYYYYY"]   # friends/family
POLICE_NUMBER = "+91ZZZZZZZZZZ"          # police emergency number for the area (if available)

client = Client(TWILIO_SID, TWILIO_TOKEN)

def send_sms(to, body):
    message = client.messages.create(body=body, from_=TWILIO_FROM, to=to)
    return message.sid

@app.route("/sos", methods=["POST"])
def sos():
    data = request.get_json(force=True)
    device_id = data.get("device_id", "unknown")
    lat = data.get("latitude")
    lon = data.get("longitude")
    ts = data.get("timestamp", time.time())
    readable_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

    if lat and lon:
        maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        body = f"SOS from device {device_id} at {readable_ts}. Location: {maps_link}"
    else:
        body = f"SOS from device {device_id} at {readable_ts}. Location not available."

    sids = []
    # notify registered numbers
    for num in REGISTERED_NUMBERS:
        try:
            sid = send_sms(num, body)
            sids.append(sid)
        except Exception as e:
            print("Failed to send to", num, e)

    # optionally notify police number
    try:
        sid = send_sms(POLICE_NUMBER, body + " (auto-alert)")
        sids.append(sid)
    except Exception as e:
        print("Failed to notify police", e)

    return jsonify({"status": "sent", "sids": sids}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
