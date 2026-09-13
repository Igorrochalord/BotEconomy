"""BotEconomy — standalone Telegram bot.

Self-contained: talks to yfinance/matplotlib/reportlab directly (via
stocks.py) and keeps its own tickers/alerts state (via storage.py). No
external backend service required — the browser companion (extension +
its own backend) lives in a separate repository and does not affect this
bot.
"""
import logging
import os
import shutil
from datetime import time as dt_time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import stocks
import storage

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
MORNING_SUMMARY_HOUR = int(os.getenv("MORNING_SUMMARY_HOUR", "6"))
EVENING_SUMMARY_HOUR = int(os.getenv("EVENING_SUMMARY_HOUR", "20"))
ALERT_CHECK_MINUTES = int(os.getenv("ALERT_CHECK_MINUTES", "15"))
TZ = ZoneInfo("America/Sao_Paulo")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bem-vindo! Aqui estão os comandos disponíveis:\n"
        "/dados - Ver dados financeiros\n"
        "/volume - Ver volume de negociação\n"
        "/relatorio - Gerar gráficos e relatório em PDF\n"
        "/addticker <TICKER> - Adicionar ação\n"
        "/removeticker <TICKER> - Remover ação\n"
        "/listtickers - Listar ações monitoradas\n"
        "/alerta <TICKER> <acima|abaixo> <preço> - Criar alerta de preço"
    )


async def dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Obtendo dados financeiros...")
    top_positive, top_negative, top_rentaveis = stocks.get_stock_data()
    if top_positive is None:
        await update.message.reply_text("Não foi possível obter os dados financeiros.")
        return

    message = "📊 *Top 10 Ações em Alta:*\n"
    for ticker, value in top_positive.items():
        message += f"📈 {ticker}: {value:.2f}%\n"
    message += "\n📉 *Top 10 Ações em Queda:*\n"
    for ticker, value in top_negative.items():
        message += f"📉 {ticker}: {value:.2f}%\n"
    message += "\n🏆 *Top 15 Ações Mais Rentáveis:*\n"
    for ticker, value in top_rentaveis.items():
        message += f"🏅 {ticker}: {value:.2f}%\n"

    await update.message.reply_text(message, parse_mode="Markdown")


async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Obtendo volume de negociação...")
    data = stocks.get_volume_summary()
    if not data:
        await update.message.reply_text("Não foi possível obter o volume de negociação.")
        return

    message = "📊 *Volume de Negociação:*\n"
    for ticker, value in data.items():
        message += f"📈 {ticker}: {value:,.0f}\n"
    await update.message.reply_text(message, parse_mode="Markdown")


async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gerando relatório...")
    pdf_path = stocks.build_report_pdf()
    if not pdf_path:
        await update.message.reply_text("Não foi possível gerar o relatório.")
        return
    try:
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(document=InputFile(f, filename="relatorio_financeiro.pdf"))
    finally:
        shutil.rmtree(os.path.dirname(pdf_path), ignore_errors=True)


async def addticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso correto: /addticker <TICKER>")
        return
    _, message = storage.add_ticker(context.args[0])
    await update.message.reply_text(message)


async def removeticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso correto: /removeticker <TICKER>")
        return
    _, message = storage.remove_ticker(context.args[0])
    await update.message.reply_text(message)


async def listtickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickers = storage.get_tickers()
    await update.message.reply_text(f"Ações monitoradas: {', '.join(tickers)}")


async def alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3 or context.args[1] not in ("acima", "abaixo"):
        await update.message.reply_text("Uso correto: /alerta <TICKER> <acima|abaixo> <preço>")
        return
    ticker, direction, price = context.args
    condition = "above" if direction == "acima" else "below"
    try:
        price = float(price.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Preço inválido.")
        return

    storage.add_alert(ticker, condition, price)
    await update.message.reply_text(f"🔔 Alerta criado: {ticker.upper()} {direction} de {price:.2f}")


async def send_daily_summary(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_ID:
        return
    top_positive, top_negative, _ = stocks.get_stock_data()
    if top_positive is None:
        return
    lines = ["📊 *Resumo Diário do Mercado*\n", "📈 *Maiores Altas:*"]
    for ticker, value in top_positive.items():
        lines.append(f"  {ticker}: {value:.2f}%")
    lines.append("\n📉 *Maiores Quedas:*")
    for ticker, value in top_negative.items():
        lines.append(f"  {ticker}: {value:.2f}%")
    await context.bot.send_message(chat_id=CHAT_ID, text="\n".join(lines), parse_mode="Markdown")


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_ID:
        return
    alerts = [a for a in storage.get_alerts() if not a["triggered"]]
    if not alerts:
        return
    tickers = list({a["ticker"] for a in alerts})
    prices = stocks.get_latest_prices(tickers)
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
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=f"{arrow} *Alerta disparado*: {alert['ticker']} atingiu "
                     f"{price:.2f} (alvo: {alert['condition']} {alert['price']:.2f})",
                parse_mode="Markdown",
            )


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dados", dados))
    application.add_handler(CommandHandler("volume", volume))
    application.add_handler(CommandHandler("relatorio", relatorio))
    application.add_handler(CommandHandler("addticker", addticker))
    application.add_handler(CommandHandler("removeticker", removeticker))
    application.add_handler(CommandHandler("listtickers", listtickers))
    application.add_handler(CommandHandler("alerta", alerta))

    if CHAT_ID:
        job_queue = application.job_queue
        job_queue.run_daily(send_daily_summary, time=dt_time(hour=MORNING_SUMMARY_HOUR, tzinfo=TZ))
        job_queue.run_daily(send_daily_summary, time=dt_time(hour=EVENING_SUMMARY_HOUR, tzinfo=TZ))
        job_queue.run_repeating(check_alerts, interval=ALERT_CHECK_MINUTES * 60, first=60)
        logger.info(
            "Resumos diários agendados (%sh/%sh) e checagem de alertas a cada %smin",
            MORNING_SUMMARY_HOUR, EVENING_SUMMARY_HOUR, ALERT_CHECK_MINUTES,
        )
    else:
        logger.info("TELEGRAM_CHAT_ID não configurado — resumo diário e alertas por push desativados.")

    application.run_polling()


if __name__ == "__main__":
    main()
