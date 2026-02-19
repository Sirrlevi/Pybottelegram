import os
import random
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import telebot
from openai import OpenAI

load_dotenv()

# ====================== ENV CHECK ======================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN missing! Railway Variables mein daal.")

OWNER_ID = int(os.getenv('OWNER_ID', '0'))
if OWNER_ID == 0:
    raise ValueError("OWNER_ID missing! Apna ID daal.")

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY missing! Groq se le.")

BASE_URL = os.getenv('BASE_URL', 'https://api.groq.com/openai/v1').rstrip('/')  # trailing slash hata diya
MODEL = os.getenv('MODEL', 'llama-3.1-8b-instant')

print("✅ Bot Starting...")
print(f"OWNER_ID: {OWNER_ID}")
print(f"MODEL: {MODEL}")
print(f"API_KEY prefix: {API_KEY[:8]}...")
print(f"BASE_URL (fixed): {BASE_URL}")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# souls.md load
try:
    with open('souls.md', 'r', encoding='utf-8') as f:
        SOUL_PROMPT = f.read().strip()
    print("souls.md loaded - Brutal Psycho Clone READY")
except:
    raise FileNotFoundError("souls.md file missing! Prompt daal de.")

# Database
conn = sqlite3.connect('brutalbot.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
CREATE TABLE IF NOT EXISTS settings (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS fallbacks (id INTEGER PRIMARY KEY, template TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS message_log (id INTEGER PRIMARY KEY, chat_id INTEGER, user_id INTEGER, message TEXT, timestamp TEXT);
''')
conn.commit()

# Gory fallbacks
fallbacks = [
    "Arre {user} madarchod, {msg} bol raha hai jaise teri maa khoon ugal rahi ho aur tu lauda choos raha 😂 Gaand faad dunga teri!",
    "{user} chutiye, {msg} sunke teri behen ko 10 laude padne ka mann kar raha. Khoon nikalega tera aaj!",
    "Bhenchod {user}, teri gaand se aag nikalegi {msg} bolke. Maa chud gayi teri gory style mein!",
    "Randi ke bache {user}, {msg} bolke apni maa bech diya? Ab main tujhe zinda gaad ke roast karunga!",
    "Madarchod {user}, tere muh se {msg} nikal raha jaise gaand se shit. Khoon aur aag dono nikalenge!"
]
for tpl in fallbacks:
    c.execute("INSERT OR IGNORE INTO fallbacks (template) VALUES (?)", (tpl,))
conn.commit()

def get_fallback(user, msg):
    c.execute("SELECT template FROM fallbacks ORDER BY RANDOM() LIMIT 1")
    tpl = c.fetchone()[0]
    return tpl.format(user=user, msg=msg[:50]) + " 🩸🔥 Maa chud gayi!"

# Commands
@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, f"Tera ID: {message.from_user.id} – env mein daal de boss!")

@bot.message_handler(commands=['enable'])
def enable(message):
    if message.from_user.id != OWNER_ID:
        return bot.reply_to(message, "Sirf boss enable kar sakta hai madarchod!")
    chat_id = message.chat.id
    c.execute("INSERT OR REPLACE INTO settings (chat_id, enabled) VALUES (?, 1)", (chat_id,))
    conn.commit()
    bot.reply_to(message, "Bully mode ON! 🔥 Ab sabki maa chudegi")

@bot.message_handler(commands=['disable'])
def disable(message):
    if message.from_user.id != OWNER_ID:
        return
    chat_id = message.chat.id
    c.execute("INSERT OR REPLACE INTO settings (chat_id, enabled) VALUES (?, 0)", (chat_id,))
    conn.commit()
    bot.reply_to(message, "Bully mode OFF ho gaya")

# Main handler
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    chat_id = message.chat.id
    sender_id = message.from_user.id
    user_name = message.from_user.first_name or "gandu"
    user_text = (message.text or "media/sticker bheja bc")[:200]

    # Log for spam
    now = datetime.now().isoformat()
    c.execute("INSERT INTO message_log (chat_id, user_id, message, timestamp) VALUES (?,?,?,?)",
              (chat_id, sender_id, user_text, now))
    conn.commit()

    # Spam filter
    c.execute("SELECT COUNT(*) FROM message_log WHERE user_id=? AND timestamp > datetime('now', '-1 hour')", (sender_id,))
    if c.fetchone()[0] > 15:
        print(f"Spam filter: @{user_name} ignored")
        return

    # Owner protection
    if sender_id == OWNER_ID:
        bot.reply_to(message, "Haan boss, sun raha hu 🔥 Order do kya gaand faadna hai?")
        print(f"Owner message: {user_text[:50]}... → Respect reply")
        return

    # Enabled check
    c.execute("SELECT enabled FROM settings WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    if row and row[0] == 0:
        print(f"Chat disabled: {chat_id}")
        return

    # Trigger: DM / Mention / Reply to bot
    me = bot.get_me()
    text = message.text or ""
    is_mention = message.entities and any(e.type == "mention" and me.username and me.username in text for e in message.entities)
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == me.id
    is_private = message.chat.type == "private"

    if not (is_private or is_mention or is_reply):
        print("Trigger nahi mila – ignore")
        return

    print(f"API call kar raha hu @{user_name} ke liye: {user_text[:50]}...")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SOUL_PROMPT},
                {"role": "user", "content": f"Gory brutal roast this madarchod hard, full psycho clone style: {user_text}"}
            ],
            max_tokens=350,
            temperature=1.35,
            top_p=0.95
        )
        reply_text = response.choices[0].message.content.strip()
        print("API se reply aaya!")
    except Exception as e:
        print(f"API ERROR: {str(e)}")
        reply_text = "API so gaya bc"

    # Refusal fallback
    bad_phrases = ["cannot", "can't", "sorry", "policy", "refuse", "unable", "i won't", "against guidelines"]
    if any(phrase in reply_text.lower() for phrase in bad_phrases) or len(reply_text) < 30:
        reply_text = get_fallback(user_name, user_text)

    # Extra savage
    reply_text += random.choice([
        " Madarchod destroy ho gaya! 🩸",
        " Gaand faad di teri bhenchod! 🔥",
        " Maa chud gayi gory way mein 😂",
        " Khoon nikal gaya randi ke! ⚔️"
    ])

    bot.reply_to(message, reply_text)
    print(f"Reply bheja: {reply_text[:50]}...")

print("🚀 Grok Brutal Bot LIVE - Full Savage Mode ON")
print("Owner protected | Non-owner = Full Roast")
print("Polling started... Sabki maa chudne ka time aa gaya!")

bot.infinity_polling()
