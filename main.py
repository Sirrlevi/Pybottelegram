import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from openai import OpenAI
from dotenv import load_dotenv

# Load .env for local testing
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROK_API_KEY = os.getenv("GROK_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing in environment variables")

if not GROK_API_KEY:
    raise ValueError("GROK_API_KEY missing in environment variables")

# Grok client (xAI OpenAI-compatible endpoint)
client = OpenAI(
    api_key=GROK_API_KEY,
    base_url="moonshotai/kimi-k2-instruct-0905",
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# -------- Language Detection --------
def detect_language(text: str) -> str:
    text_lower = text.lower()

    hindi_words = ["hai", "kya", "kaise", "bhai", "tum", "kyu", "mat", "nahi"]
    if any(word in text_lower for word in hindi_words):
        if all(ord(c) < 128 for c in text_lower):
            return "hinglish"
        return "hindi"

    return "english"


def build_system_prompt(lang: str) -> str:
    if lang == "hindi":
        return (
            "Tum ek intelligent aur context-aware assistant ho. "
            "Har message ko samajh kar reply do. Generic ya robotic reply mat do."
        )
    elif lang == "hinglish":
        return (
            "Tu ek smart assistant hai. Context samajh ke natural reply de. "
            "Copy-paste type ya boring response mat de."
        )
    else:
        return (
            "You are a sharp and context-aware assistant. "
            "Avoid generic responses. Think before replying."
        )


# -------- AI Response Generator --------
async def generate_reply(user_text: str) -> str:
    lang = detect_language(user_text)
    system_prompt = build_system_prompt(lang)

    # Run blocking API call in separate thread
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="grok-beta",  # Change if needed
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.7,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()


# -------- Handlers --------
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer("Bot online. Bolo kya chahiye.")


@dp.message()
async def chat_handler(message: Message):
    try:
        user_text = message.text

        if not user_text:
            return

        reply = await generate_reply(user_text)
        await message.answer(reply)

    except Exception as e:
        print("ERROR:", e)
        await message.answer("Error processing request.")


# -------- Main Runner --------
async def main():
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
