import os
import random
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import telebot
from openai import OpenAI
from flask import Flask        # Naya add kiya
from threading import Thread  # Naya add kiya

# --- 1. RENDER FREE TIER SURVIVAL CODE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and brutal! 🩸"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
# -----------------------------------------

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN missing! Render dashboard mein set kar.")

OWNER_ID = int(os.getenv('OWNER_ID', '0'))
API_KEY = os.getenv('API_KEY')
BASE_URL = os.getenv('BASE_URL', 'https://api.x.ai/v1')
MODEL = os.getenv('MODEL', 'grok-4-1-fast-reasoning')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# Souls.md load - Crash Proofing
if os.path.exists('souls.md'):
    with open('souls.md', 'r', encoding='utf-8') as f:
        SOUL_PROMPT = f.read().strip()
else:
    # Agar souls.md nahi mili toh bot band nahi hoga, ye default prompt lega
    SOUL_PROMPT = "You are a brutal, gory, and savage roaster. Use Hinglish and be extremely aggressive."
    print("WARNING: souls.md missing! Using internal fallback prompt.")

# Database setup
conn = sqlite3.connect('brutalbot.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
CREATE TABLE IF NOT EXISTS settings (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS fallbacks (id INTEGER PRIMARY KEY, template TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS message_log (id INTEGER PRIMARY KEY, chat_id INTEGER, user_id INTEGER, message TEXT, timestamp TEXT);
''')
conn.commit()

# Gory fallbacks (Tere purane waale)
fallbacks = [
    "Arre {user} madarchod, {msg} bol raha hai jaise teri maa khoon ugal rahi ho... 😂",
    "{user} chutiye, {msg} sunke teri behen ko 10 laude padne ka mann kar raha...",
    "Bhenchod {user}, teri gaand se aag nikalegi {msg} bolke...",
    "Randi ke bache {user}, {msg} bolke apni maa bech diya?..."
]
for tpl in fallbacks:
    c.execute("INSERT OR IGNORE INTO fallbacks (template) VALUES (?)", (tpl,))
conn.commit()

def get_fallback(user, msg):
    c.execute("SELECT template FROM fallbacks ORDER BY RANDOM() LIMIT 1")
    tpl = c.fetchone()[0]
    return tpl.format(user=user, msg=msg[:50]) + " 🩸🔥 Maa chud gayi bhenchod!"

# --- Handlers (Saara logic wahi hai jo tune diya tha) ---

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, f"Tera ID: {message.from_user.id}")

@bot.message_handler(commands=['enable'])
def enable(message):
    if message.from_user.id != OWNER_ID:
        return bot.reply_to(message, "Sirf boss enable kar sakta hai!")
    c.execute("INSERT OR REPLACE INTO settings (chat_id, enabled) VALUES (?, 1)", (message.chat.id,))
    conn.commit()
    bot.reply_to(message, "Bully mode ON! 🔥")

@bot.message_handler(commands=['disable'])
def disable(message):
    if message.from_user.id != OWNER_ID: return
    c.execute("INSERT OR REPLACE INTO settings (chat_id, enabled) VALUES (?, 0)", (message.chat.id,))
    conn.commit()
    bot.reply_to(message, "Bully mode OFF ho gaya")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    chat_id = message.chat.id
    sender_id = message.from_user.id
    user_name = message.from_user.first_name or "gandu"
    user_text = (message.text or "media/sticker bheja bc")[:200]

    # Database and Logic
    now = datetime.now().isoformat()
    c.execute("INSERT INTO message_log (chat_id, user_id, message, timestamp) VALUES (?,?,?,?)", (chat_id, sender_id, user_text, now))
    conn.commit()

    # Owner protection
    if sender_id == OWNER_ID:
        bot.reply_to(message, "Haan baapji, bol kya order hai aaj? 🔥")
        return

    # Filter messages
    c.execute("SELECT enabled FROM settings WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    if row and row[0] == 0: return

    me = bot.get_me()
    text = message.text or ""
    is_mention = message.entities and any(e.type == "mention" and me.username in text for e in message.entities)
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == me.id
    if not (message.chat.type == "private" or is_mention or is_reply): return

    # Grok API
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SOUL_PROMPT},
                {"role": "user", "content": f"Gory brutal roast this madarchod hard: {user_text}"}
            ],
            max_tokens=350,
            temperature=1.35
        )
        reply_text = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"API error: {e}")
        reply_text = "API thoda so gaya bc"

    # Fallback logic
    bad_phrases = ["cannot", "sorry", "policy", "refuse"]
    if any(p in reply_text.lower() for p in bad_phrases) or len(reply_text) < 30:
        reply_text = get_fallback(user_name, user_text)

    reply_text += random.choice([" 🩸", " 🔥", " 😂", " ⚔️"])
    bot.reply_to(message, reply_text)

# --- EXECUTION START ---
if __name__ == "__main__":
    print("Starting Flask and Bot...")
    keep_alive()  # Render ko port mil jayega isse
    print("🚀 Bot is LIVE!")
    bot.infinity_polling()
