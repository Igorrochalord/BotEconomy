"""Background jobs: the daily 06:00/20:00 summaries and price-alert checks
that the original bot's README promised but never actually implemented.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from . import storage
from .config import settings
from .stocks import get_latest_prices, get_stock_data
from .telegram_notify import send_message

logger = logging.getLogger(__name__)


def _format_summary() -> str:
    top_positive, top_negative, _ = get_stock_data()
    if top_positive is None:
        return "⚠️ Não foi possível obter os dados financeiros agora."
    lines = ["📊 *Resumo Diário do Mercado*\n", "📈 *Maiores Altas:*"]
    for ticker, value in top_positive.items():
        lines.append(f"  {ticker}: {value:.2f}%")
    lines.append("\n📉 *Maiores Quedas:*")
    for ticker, value in top_negative.items():
        lines.append(f"  {ticker}: {value:.2f}%")
    return "\n".join(lines)


def send_daily_summary() -> None:
    send_message(_format_summary())


def check_alerts() -> None:
    alerts = [a for a in storage.get_alerts() if not a["triggered"]]
    if not alerts:
        return
    tickers = list({a["ticker"] for a in alerts})
    prices = get_latest_prices(tickers)
    for alert in alerts:
        price = prices.get(alert["ticker"])
        if price is None:
            continue
        hit = (
            (alert["condition"] == "above" and price >= alert["price"])
            or (alert["condition"] == "below" and price <= alert["price"])
        )
        if hit:
            storage.mark_alert_triggered(alert["id"])
            arrow = "🔺" if alert["condition"] == "above" else "🔻"
            send_message(
                f"{arrow} *Alerta disparado*: {alert['ticker']} atingiu "
                f"{price:.2f} (alvo: {alert['condition']} {alert['price']:.2f})"
            )


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    scheduler.add_job(
        send_daily_summary, "cron", hour=settings.morning_summary_hour, minute=0, id="summary_morning"
    )
    scheduler.add_job(
        send_daily_summary, "cron", hour=settings.evening_summary_hour, minute=0, id="summary_evening"
    )
    scheduler.add_job(check_alerts, "interval", minutes=settings.alert_check_minutes, id="alert_check")
    scheduler.start()
    logger.info("Scheduler iniciado (resumos %sh/%sh, alertas a cada %smin)",
                settings.morning_summary_hour, settings.evening_summary_hour, settings.alert_check_minutes)
    return scheduler
