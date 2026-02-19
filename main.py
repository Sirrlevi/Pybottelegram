import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from openai import OpenAI
from dotenv import load_dotenv

# Load local .env (Railway pe automatic ENV use hoga)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROK_API_KEY = os.getenv("GROK_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")
if not GROK_API_KEY:
    raise ValueError("GROK_API_KEY missing")

# Grok Client (xAI OpenAI-compatible endpoint)
client = OpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.x.ai/v1",
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Language detection (basic but effective)
def detect_language(text: str) -> str:
    text_lower = text.lower()
    if any(word in text_lower for word in ["hai", "kya", "kaise", "bhai", "tum", "mat", "kyu"]):
        if any(c.isalpha() for c in text_lower):
            return "hinglish"
        return "hindi"
    return "english"


def build_system_prompt(lang: str) -> str:
    if lang == "hindi":
        return "Tum ek intelligent, context-aware assistant ho. Soch samajh kar jawab do. Saved replies mat spam karo."
    elif lang == "hinglish":
        return "Tu ek smart assistant hai. Context samajh ke reply de. Bakwaas copy-paste ya robotic reply nahi."
    else:
        return "You are a sharp, context-aware assistant. Avoid generic replies. Think before responding."


async def generate_reply(user_text: str) -> str:
    lang = detect_language(user_text)
    system_prompt = build_system_prompt(lang)

    response = client.chat.completions.create(
        model="grok-beta",   # change if needed
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.7,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Bot online. Bolo kya chahiye.")


@dp.message()
async def chat_handler(message: Message):
    try:
        user_text = message.text
        reply = await asyncio.to_thread(generate_reply, user_text)
        await message.answer(reply)
    except Exception as e:
        await message.answer("Error processing request.")
        print("ERROR:", e)


async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
