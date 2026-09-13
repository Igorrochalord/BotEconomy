import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    allowed_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ]
    api_key: str = os.getenv("BOTECONOMY_API_KEY", "").strip()
    port: int = int(os.getenv("PORT", "8000"))
    morning_summary_hour: int = int(os.getenv("MORNING_SUMMARY_HOUR", "6"))
    evening_summary_hour: int = int(os.getenv("EVENING_SUMMARY_HOUR", "20"))
    alert_check_minutes: int = int(os.getenv("ALERT_CHECK_MINUTES", "15"))


settings = Settings()
