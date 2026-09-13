"""Minimal Telegram push helper.

Uses plain HTTP calls to the Bot API instead of pulling in the full
python-telegram-bot dependency here — the backend only ever *sends*
messages (alerts, daily summaries); it never needs to poll for updates.
"""
import logging

import requests

from .config import settings

logger = logging.getLogger(__name__)


def send_message(text: str) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID não configurados; mensagem não enviada.")
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": settings.telegram_chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Falha ao enviar mensagem para o Telegram")
        return False
