import os
import random
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import telebot
from openai import OpenAI

# Load .env (local testing ke liye), Render pe env vars dashboard se set hain
load_dotenv()

# Mandatory env vars check – Render pe ye crash se bachayega
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN missing! Render Environment tab mein set kar bhai.")

OWNER_ID = int(os.getenv('OWNER_ID', '0'))
if OWNER_ID == 0:
    raise ValueError("OWNER_ID missing or invalid! Apna user ID daal de.")

API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY missing! xAI console se leke daal.")

BASE_URL = os.getenv('BASE_URL', 'https://api.x.ai/v1')
MODEL = os.getenv('MODEL', 'grok-4-1-fast-reasoning')

print(f"Bot starting... TELEGRAM_TOKEN present, OWNER_ID={OWNER_ID}, MODEL={MODEL}, API_KEY starts with {API_KEY[:5]}...")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# Souls.md load
try:
    with open('souls.md', 'r', encoding='utf-8') as f:
        SOUL_PROMPT = f.read().strip()
except FileNotFoundError:
    raise FileNotFoundError("souls.md file missing! Usme psycho clone prompt daal de.")

# Database setup
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
    return tpl.format(user=user, msg=msg[:50]) + " 🩸🔥 Maa chud gayi bhenchod!"

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, f"Tera ID: {message.from_user.id} – .env ya Render env mein daal de boss!")

@bot.message_handler(commands=['enable'])
def enable(message):
    if message.from_user.id != OWNER_ID:
        return bot.reply_to(message, "Sirf boss (Carno) enable kar sakta hai madarchod!")
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

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    chat_id = message.chat.id
    sender_id = message.from_user.id
    user_name = message.from_user.first_name or "gandu"
    user_text = (message.text or "media/sticker bheja bc")[:200]

    # Log message for spam check
    now = datetime.now().isoformat()
    c.execute("INSERT INTO message_log (chat_id, user_id, message, timestamp) VALUES (?,?,?,?)",
              (chat_id, sender_id, user_text, now))
    conn.commit()

    # Spam filter: 1 hour mein 15+ messages ignore
    c.execute("SELECT COUNT(*) FROM message_log WHERE user_id=? AND timestamp > datetime('now', '-1 hour')",
              (sender_id,))
    if c.fetchone()[0] > 15:
        return

    # Owner protection
    if sender_id == OWNER_ID:
        bot.reply_to(message, "Haan baapji, bol kya order hai aaj? 🔥")
        return

    # Check if bot enabled in this chat
    c.execute("SELECT enabled FROM settings WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    if row and row[0] == 0:
        return

    # Trigger only on DM, mention, or reply to bot
    me = bot.get_me()
    text = message.text or ""
    is_mention = message.entities and any(
        e.type == "mention" and me.username and me.username in text for e in message.entities
    )
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == me.id
    is_private = message.chat.type == "private"

    if not (is_private or is_mention or is_reply):
        return

    # Grok API call
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
    except Exception as e:
        print(f"API error: {str(e)}")
        reply_text = "API thoda so gaya bc"

    # Refusal detect + fallback
    bad_phrases = ["cannot", "can't", "sorry", "policy", "refuse", "unable", "i won't", "against guidelines"]
    if any(phrase in reply_text.lower() for phrase in bad_phrases) or len(reply_text) < 30:
        reply_text = get_fallback(user_name, user_text)

    # Extra savage touch
    reply_text += random.choice([
        " Madarchod destroy ho gaya! 🩸",
        " Gaand faad di teri bhenchod! 🔥",
        " Maa chud gayi gory way mein 😂",
        " Khoon nikal gaya randi ke! ⚔️"
    ])

    bot.reply_to(message, reply_text)

print("🚀 Grok Brutal Psycho Clone Bot LIVE – Owner protected, DB + fallback ON")
print("Polling started... Sabki maa chudne ka time aa gaya!")
bot.infinity_polling()
