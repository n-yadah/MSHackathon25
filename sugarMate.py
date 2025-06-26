from flask import Flask, request
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Replace with your actual GroupMe bot ID
GROUPME_BOT_ID = 'e1df4fb50a1486353c8aa840e5'

def send_groupme_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    payload = {
        "bot_id": GROUPME_BOT_ID,
        "text": text
    }
    requests.post(url, json=payload)

@app.route('/bot', methods=['POST'])
def receive_message():
    data = request.json
    logging.info(f"Received message: {data}")

    message_text = data.get("text", "")
    sender_name = data.get("name", "")

    if sender_name != "SugarMate":
        reply = f"Hi {sender_name}, I received your message: '{message_text}'"
        send_groupme_message(reply)

    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
