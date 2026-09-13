"""BotEconomy — Telegram front-end.

Thin client over the shared BotEconomy backend API: all market-data
fetching, chart/PDF generation and ticker/alert state now live in
`backend/`, so this bot and the Chrome extension never drift apart.
"""
import logging
import os

import requests
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_BASE_URL = os.getenv("BOTECONOMY_API_URL", "http://localhost:8000")
API_KEY = os.getenv("BOTECONOMY_API_KEY", "")


def _headers():
    return {"X-API-Key": API_KEY} if API_KEY else {}


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
    resp = requests.get(f"{API_BASE_URL}/api/summary", timeout=30)
    if resp.status_code != 200:
        await update.message.reply_text("Não foi possível obter os dados financeiros.")
        return

    data = resp.json()
    message = "📊 *Top 10 Ações em Alta:*\n"
    for ticker, value in data["top_positive"].items():
        message += f"📈 {ticker}: {value:.2f}%\n"
    message += "\n📉 *Top 10 Ações em Queda:*\n"
    for ticker, value in data["top_negative"].items():
        message += f"📉 {ticker}: {value:.2f}%\n"
    message += "\n🏆 *Top 15 Ações Mais Rentáveis:*\n"
    for ticker, value in data["top_rentaveis"].items():
        message += f"🏅 {ticker}: {value:.2f}%\n"

    await update.message.reply_text(message, parse_mode="Markdown")


async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Obtendo volume de negociação...")
    resp = requests.get(f"{API_BASE_URL}/api/volume", timeout=30)
    if resp.status_code != 200:
        await update.message.reply_text("Não foi possível obter o volume de negociação.")
        return

    message = "📊 *Volume de Negociação:*\n"
    for ticker, value in resp.json()["volume"].items():
        message += f"📈 {ticker}: {value:,.0f}\n"
    await update.message.reply_text(message, parse_mode="Markdown")


async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gerando relatório...")
    resp = requests.get(f"{API_BASE_URL}/api/report", timeout=120)
    if resp.status_code != 200:
        await update.message.reply_text("Não foi possível gerar o relatório.")
        return
    await update.message.reply_document(document=InputFile(resp.content, filename="relatorio_financeiro.pdf"))


async def addticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso correto: /addticker <TICKER>")
        return
    resp = requests.post(
        f"{API_BASE_URL}/api/tickers", json={"ticker": context.args[0]}, headers=_headers(), timeout=15
    )
    await update.message.reply_text(resp.json().get("message", resp.json().get("detail", "Erro.")))


async def removeticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso correto: /removeticker <TICKER>")
        return
    resp = requests.delete(f"{API_BASE_URL}/api/tickers/{context.args[0]}", headers=_headers(), timeout=15)
    await update.message.reply_text(resp.json().get("message", resp.json().get("detail", "Erro.")))


async def listtickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resp = requests.get(f"{API_BASE_URL}/api/tickers", timeout=15)
    tickers = resp.json().get("tickers", [])
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

    resp = requests.post(
        f"{API_BASE_URL}/api/alerts",
        json={"ticker": ticker, "condition": condition, "price": price},
        headers=_headers(),
        timeout=15,
    )
    if resp.status_code == 200:
        await update.message.reply_text(f"🔔 Alerta criado: {ticker.upper()} {direction} de {price:.2f}")
    else:
        await update.message.reply_text(resp.json().get("detail", "Não foi possível criar o alerta."))


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
    application.run_polling()


if __name__ == "__main__":
    main()
