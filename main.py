import os
import telebot
from groq import Groq

# Tokens from ENV
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

print("Bot started...")

# Initialize clients
bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "✅ Bot online.\nBolo kya chahiye.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_text = message.text

        completion = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct-0905",
            messages=[
                {
                    "role": "system",
                    "content": "Reply in clear slide format with headings and sections."
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            temperature=0.7,
            max_tokens=800
        )

        ai_reply = completion.choices[0].message.content

        # Slide format
        final_reply = f"""
━━━━━━━━━━━━━━━━━━
📢 AI RESPONSE SLIDE
━━━━━━━━━━━━━━━━━━

📝 Your Message:
{user_text}

🤖 AI Reply:
{ai_reply}

━━━━━━━━━━━━━━━━━━
"""

        bot.reply_to(message, final_reply)

    except Exception as e:
        print("FULL ERROR:", str(e))
        bot.reply_to(message, f"⚠️ System Error:\n{str(e)}")


bot.infinity_polling()
