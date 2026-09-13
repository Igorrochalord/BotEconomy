import os

# bot.py reads this at import time; tests never talk to the real Telegram API.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("BOTECONOMY_API_URL", "http://testserver")
