from flask import Flask, request
import requests
import logging
import openai
from openai import OpenAI
import os
import json
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Load API keys
GROUPME_BOT_ID = os.getenv("GROUPME_BOT_ID")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# File to store conversation history
CHAT_LOG_FILE = "chat_log.json"

# Load or initialize chat log
if os.path.exists(CHAT_LOG_FILE):
    with open(CHAT_LOG_FILE, "r") as f:
        conversation_history = json.load(f)
else:
    conversation_history = []

# Health log and preferences files
HEALTH_LOG_FILE = "health_log.json"
PREFS_FILE = "preferences.json"

def load_json_file(filename, default):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return default
    return default

def save_json_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

health_log = load_json_file(HEALTH_LOG_FILE, [])
preferences = load_json_file(PREFS_FILE, {})

def save_chat_log():
    with open(CHAT_LOG_FILE, "w") as f:
        json.dump(conversation_history, f, indent=2)

def send_groupme_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    payload = {
        "bot_id": GROUPME_BOT_ID,
        "text": text
    }
    requests.post(url, json=payload)

def log_health_entry(user, entry):
    entry['user'] = user
    entry['timestamp'] = datetime.datetime.now().isoformat()
    health_log.append(entry)
    save_json_file(HEALTH_LOG_FILE, health_log)

def set_user_pref(user, key, value):
    if user not in preferences:
        preferences[user] = {}
    preferences[user][key] = value
    save_json_file(PREFS_FILE, preferences)

def get_user_pref(user, key, default=None):
    return preferences.get(user, {}).get(key, default)

def is_emergency(text):
    keywords = ["help", "emergency", "dizzy", "unconscious", "faint", "urgent"]
    return any(word in text.lower() for word in keywords)

def get_resource_tip():
    tips = [
        "Check out the ADA's diabetes tips: https://diabetes.org/healthy-living",
        "Remember to stay hydrated and monitor your sugar levels regularly.",
        "Here's a guide on managing diabetes: https://www.cdc.gov/diabetes/managing/index.html"
    ]
    return tips[datetime.datetime.now().second % len(tips)]

def extract_health_log_with_ai(user_message):
    prompt = [
        {"role": "system", "content": (
            "You are an assistant that extracts structured health log data from user messages. "
            "If the message contains information about blood sugar, meals, or medication, "
            "return a JSON object with keys: 'category' (sugar/meal/medication), 'value', and 'time' if available. "
            "If not, return null."
        )},
        {"role": "user", "content": user_message}
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=prompt,
            temperature=0
        )
        content = response.choices[0].message.content
        # Try to parse JSON from the AI's response
        data = None
        try:
            data = json.loads(content)
        except Exception:
            pass
        return data
    except Exception as e:
        logging.error(f"OpenAI log extraction error: {e}")
        return None

def get_ai_response(user_message):
    conversation_history.append({"role": "user", "content": user_message})
    messages = [
        {"role": "system", "content": "You are SugarMate, a friendly and supportive diabetes health assistant. Be concise, helpful, and kind."}
    ] + conversation_history[-5:]

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": reply})
        save_chat_log()
        return reply
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "Sorry, I had trouble thinking that through. Try again?"

@app.route('/bot', methods=['POST'])
def receive_message():
    data = request.json
    logging.info(f"Received message: {data}")

    message_text = data.get("text", "")
    sender_name = data.get("name", "")

    # Privacy controls: opt-in/out
    if message_text.lower().startswith("opt out"):
        set_user_pref(sender_name, "opted_in", False)
        send_groupme_message("You've opted out of SugarMate's health logging and alerts.")
        return "OK", 200
    if message_text.lower().startswith("opt in"):
        set_user_pref(sender_name, "opted_in", True)
        send_groupme_message("You're now opted in to SugarMate's health logging and alerts.")
        return "OK", 200
    if get_user_pref(sender_name, "opted_in", True) is False:
        return "OK", 200

    # Health data logging via AI
    health_entry = extract_health_log_with_ai(message_text)
    if health_entry:
        log_health_entry(sender_name, health_entry)
        send_groupme_message(f"Logged {health_entry['category']}: {health_entry['value']}")
        return "OK", 200

    # Set reminders (simple: "remind me to check sugar at 8am")
    import re
    remind_match = re.match(r"remind me to ([\w\s]+) at ([\d:apm\s]+)", message_text, re.IGNORECASE)
    if remind_match:
        action = remind_match.group(1).strip()
        time_str = remind_match.group(2).strip()
        set_user_pref(sender_name, "reminder", {"action": action, "time": time_str})
        send_groupme_message(f"Reminder set to {action} at {time_str}")
        return "OK", 200

    # Emergency detection
    if is_emergency(message_text):
        send_groupme_message("Emergency detected! Please check on the user or contact a healthcare provider immediately.")
        return "OK", 200

    # Resource sharing
    if "resource" in message_text.lower() or "tip" in message_text.lower():
        send_groupme_message(get_resource_tip())
        return "OK", 200

    # Proactive alerts (basic: check reminder on each message)
    reminder = get_user_pref(sender_name, "reminder")
    if reminder:
        now = datetime.datetime.now().strftime("%I:%M%p").lower()
        if reminder["time"].replace(" ", "").lower() in now.replace(" ", ""):
            send_groupme_message(f"Reminder: {reminder['action']}")

    if sender_name != "SugarMate" and message_text:
        ai_reply = get_ai_response(message_text)
        send_groupme_message(ai_reply)

    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
