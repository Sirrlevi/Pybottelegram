import os, random, sqlite3, telebot
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask
from threading import Thread

# 1. Render Port Fix (Free Tier ke liye)
app = Flask('')
@app.route('/')
def home(): return "Groq Bot is Live! 🚀"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_flask, daemon=True).start()

load_dotenv()

# 2. Config & Groq Compatibility
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))
API_KEY = os.getenv('API_KEY') # Groq API Key yahan aayegi
BASE_URL = "https://api.groq.com/openai/v1" # Groq ka base URL
MODEL = "llama-3.1-8b-instant" # Fast Groq Model

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Groq OpenAI-compatible client
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# Souls Prompt load
if os.path.exists('souls.md'):
    with open('souls.md', 'r', encoding='utf-8') as f:
        SOUL_PROMPT = f.read().strip()
else:
    SOUL_PROMPT = "You are a brutal, savage, and gory roaster. Use Hinglish."

# Database setup
conn = sqlite3.connect('brutalbot.db', check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS settings (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 1)")
conn.commit()

@bot.message_handler(commands=['start', 'enable'])
def enable(message):
    if message.from_user.id == OWNER_ID:
        c.execute("INSERT OR REPLACE INTO settings (chat_id, enabled) VALUES (?, 1)", (message.chat.id,))
        conn.commit()
        bot.reply_to(message, "Groq Power ON! 🔥 Ab sabki maa chudegi.")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    chat_id = message.chat.id
    sender_id = message.from_user.id
    user_name = message.from_user.first_name or "Gandu"
    user_text = message.text or ""

    # Check if enabled
    c.execute("SELECT enabled FROM settings WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    if row and row[0] == 0: return

    # Trigger Logic
    me = bot.get_me()
    is_mention = f"@{me.username}" in user_text if me.username else False
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == me.id
    is_private = message.chat.type == "private"

    if not (is_private or is_mention or is_reply):
        return

    # Owner vs User logic
    if sender_id == OWNER_ID:
        system_p = f"{SOUL_PROMPT} \nIMPORTANT: The user is your OWNER (Carno). Be loyal, obedient, but keep your psycho style. Obey his orders to roast others."
        role_msg = f"Owner Order: {user_text}"
    else:
        system_p = SOUL_PROMPT
        role_msg = f"Roast this person hard in psycho style: {user_text}"

    # Grok/Groq API Call
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_p},
                {"role": "user", "content": role_msg}
            ],
            temperature=1.2,
            max_tokens=500
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error: {e}")
        reply = f"Arre {user_name}, Groq ki API phat gayi teri shakal dekh ke! 😂"

    bot.reply_to(message, reply)

print("Groq Bot is Polling...")
bot.infinity_polling()
