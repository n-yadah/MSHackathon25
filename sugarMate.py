from flask import Flask, request
import requests
import logging
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
# Removed OpenAI client initialization

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

# Removed extract_health_log_with_ai (AI log extraction)

# Removed get_ai_response (AI chat)

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

    # Keyword-based demo scenario logic
    msg = message_text.lower().strip()
    import re

    # Hardcoded demo scenario for hackathon video

    if "eggs and toast for breakfast" in msg:
        send_groupme_message("Breakfast logged. Remember to check your blood sugar in 2 hours.")
        return "OK", 200

    if "my sugar is 180" in msg or ("sugar" in msg and "180" in msg):
        send_groupme_message("Your blood sugar is a bit high. Consider a walk or some water. If this keeps happening, I can notify your healthcare provider, Dr. Smith.")
        return "OK", 200

    if "about to have lunch" in msg:
        send_groupme_message("Lunch logged. Don't forget to take your medication if needed.")
        return "OK", 200

    if "feel shaky" in msg or ("sugar" in msg and "low" in msg):
        send_groupme_message("Your blood sugar is low. Please have a quick snack or juice and recheck in 15 minutes. If you need help, I can contact Dr. Smith for you.")
        return "OK", 200

    if "forgot to take my insulin" in msg:
        send_groupme_message("If you forgot your insulin, please contact your healthcare provider for advice.")
        return "OK", 200

    if "remind me what i had for breakfast" in msg:
        send_groupme_message("You had eggs and toast for breakfast today.")
        return "OK", 200

    if "show me what i’ve logged today" in msg or "show me what i've logged today" in msg:
        send_groupme_message("Here’s your recent log: Breakfast at 8am (eggs and toast), Sugar 180 at 9am, Lunch at 12pm.")
        return "OK", 200

    if "thanks" in msg or "thank you" in msg:
        send_groupme_message("You're welcome! Let me know if you need anything else.")
        return "OK", 200

    if "good night" in msg or "heading to bed" in msg:
        send_groupme_message("Good night! Remember to check your sugar before bed.")
        return "OK", 200

    # fallback to previous generic keywords for other demo flexibility
    if "log breakfast" in msg:
        send_groupme_message("Breakfast logged. Remember to check your blood sugar in 2 hours.")
        return "OK", 200

    if "log lunch" in msg:
        send_groupme_message("Lunch logged. Don't forget to take your medication if needed.")
        return "OK", 200

    if "log dinner" in msg:
        send_groupme_message("Dinner logged. Make sure to check your sugar before bed.")
        return "OK", 200

    if "forgot insulin" in msg:
        send_groupme_message("If you forgot your insulin, please contact your healthcare provider for advice.")
        return "OK", 200

    if "my sugar is low" in msg or "low sugar" in msg:
        send_groupme_message("Your blood sugar is low. Please have a quick snack or juice and recheck in 15 minutes.")
        return "OK", 200

    sugar_match = re.match(r"my sugar is (\d+)", msg)
    if sugar_match:
        sugar_val = int(sugar_match.group(1))
        if sugar_val > 140:
            send_groupme_message("Your blood sugar is a bit high. Consider a walk or some water.")
        else:
            send_groupme_message("Your blood sugar looks good. Keep it up!")
        return "OK", 200

    if "remind me to take insulin" in msg:
        set_user_pref(sender_name, "reminder", {"action": "take insulin", "time": "in 30 minutes"})
        send_groupme_message("Insulin reminder set. I’ll notify you in 30 minutes.")
        return "OK", 200

    if "show my log" in msg:
        send_groupme_message("Here’s your recent log: Breakfast at 8am, Sugar 180 at 9am, Lunch at 12pm, Dinner at 7pm.")
        return "OK", 200

    if "help" in msg:
        send_groupme_message("You can log meals, record sugar levels, or set reminders. Try: 'log lunch', 'my sugar is 120', or 'forgot insulin'.")
        return "OK", 200

    # Emergency detection
    if is_emergency(message_text):
        send_groupme_message("Emergency detected! Please check on the user or contact a healthcare provider immediately.")
        return "OK", 200

    # Resource sharing
    if "resource" in msg or "tip" in msg:
        send_groupme_message(get_resource_tip())
        return "OK", 200

    # Proactive alerts (basic: check reminder on each message)
    reminder = get_user_pref(sender_name, "reminder")
    if reminder:
        now = datetime.datetime.now().strftime("%I:%M%p").lower()
        if reminder["time"].replace(" ", "").lower() in now.replace(" ", ""):
            send_groupme_message(f"Reminder: {reminder['action']}")

    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
