"""Diagnostic — what does Telegram itself say is the latest message on the channel?"""
import asyncio, os
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE = os.getenv("TELEGRAM_PHONE", "")
CHANNEL = os.getenv("CHANNEL", "salafimarriage1")
SESSION = Path(__file__).parent / "telegram-session"

async def main():
    async with TelegramClient(str(SESSION), API_ID, API_HASH) as client:
        await client.start(phone=PHONE)
        entity = await client.get_entity(CHANNEL)
        print(f"Channel id        : {entity.id}")
        print(f"Channel username  : @{getattr(entity, 'username', '?')}")
        print(f"Channel title     : {getattr(entity, 'title', '?')}")
        print()
        print("Latest 10 messages from Telegram (newest first):")
        async for msg in client.iter_messages(entity, limit=10):
            text = (msg.text or "")[:80].replace("\n", " ")
            print(f"  msg_id={msg.id:>6}  {msg.date.isoformat()}  {text!r}")

asyncio.run(main())
