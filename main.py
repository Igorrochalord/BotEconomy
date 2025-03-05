import os
import logging
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Define o backend para 'Agg'
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from telegram import Update, InputFile, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from bs4 import BeautifulSoup

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TICKERS = [
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC', 'TFC', 'BK',
    'STT', 'COF', 'AXP', 'DFS', 'ALLY', 'KEY', 'FITB', 'HBAN', 'RF', 'CMA'
]

def extract_news_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    news_items = soup.find_all('section', class_='container sz-small block vertical switch-to-horizontal titleCase yf-82qtw3')
    urls = []
    for item in news_items:
        news_link = item.find('a', class_='subtle-link fin-size-small titles noUnderline yf-1xqzjha')['href']
        urls.append(news_link)
    return urls

async def send_to_telegram(bot_token, chat_id, message):
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)

# Adicionar um novo ticker
def add_ticker(ticker):
    ticker = ticker.upper()
    if ticker.isalpha() and len(ticker) == 5 and not ticker.endswith('.SA'):
        ticker += ".SA"

    if ticker not in TICKERS:
        TICKERS.append(ticker)
        return f'Ticker {ticker} adicionado com sucesso!'
    return f'Ticker {ticker} já está na lista.'

def remove_ticker(ticker):
    ticker = ticker.upper()
    if ticker in TICKERS:
        TICKERS.remove(ticker)
        return f'Ticker {ticker} removido com sucesso!'
    return f'Ticker {ticker} não encontrado na lista.'

def get_stock_data():
    try:
        data = yf.download(TICKERS, period="2d", group_by="ticker", auto_adjust=True)
        if data.empty:
            return None, None, None
        valid_tickers = [ticker for ticker in TICKERS if ticker in data.columns.get_level_values(0)]
        if not valid_tickers:
            return None, None, None

        adj_close = data.xs('Close', level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
        if len(adj_close) < 2:
            return None, None, None

        returns = adj_close.pct_change(fill_method=None).iloc[-1] * 100
        top_positive = returns.sort_values(ascending=False).head(10)  # Top 10 em alta
        top_negative = returns.sort_values().head(10)  # Top 10 em queda
        top_rentaveis = returns.sort_values(ascending=False).head(15)  # Top 15 mais rentáveis
        return top_positive, top_negative, top_rentaveis
    except Exception as e:
        logging.error(f"Erro ao obter dados: {e}")
        return None, None, None

def get_volume_data():
    try:
        data = yf.download(TICKERS, period="1mo", group_by="ticker", auto_adjust=True)
        if data.empty:
            return None
        valid_tickers = [ticker for ticker in TICKERS if ticker in data.columns.get_level_values(0)]
        if not valid_tickers:
            return None

        volume = data.xs('Volume', level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data['Volume']
        return volume
    except Exception as e:
        logging.error(f"Erro ao obter volume: {e}")
        return None

def gerar_grafico_barras(top_positive, top_negative, filename):
    try:
        plt.figure(figsize=(12, 6))
        bars_pos = plt.bar(top_positive.index, top_positive.values, color='green', label='Top 10 em Alta')
        bars_neg = plt.bar(top_negative.index, top_negative.values, color='red', label='Top 10 em Queda')
        for bar in bars_pos + bars_neg:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.2f}%',
                     ha='center', va='bottom', fontsize=8)

        plt.xlabel("Ticker")
        plt.ylabel("Variação Percentual")
        plt.title("Top 10 Ações em Alta e Queda")
        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        return filename
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico de barras: {e}")
        return None

def gerar_grafico_precos(filename):
    try:
        data = yf.download(TICKERS, period="1mo", group_by="ticker", auto_adjust=True)
        if data.empty:
            return None
        valid_tickers = [ticker for ticker in TICKERS if ticker in data.columns.get_level_values(0)]
        if not valid_tickers:
            return None

        adj_close = data.xs('Close', level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data

        plt.figure(figsize=(12, 6))
        for ticker in valid_tickers:
            plt.plot(adj_close.index, adj_close[ticker], label=ticker)

        plt.xlabel("Data")
        plt.ylabel("Preço de Fechamento Ajustado")
        plt.legend()
        plt.title("Evolução dos Preços das Ações")
        plt.grid()
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        return filename
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico de preços: {e}")
        return None

def gerar_grafico_volume(filename):
    try:
        volume = get_volume_data()
        if volume is None:
            return None

        plt.figure(figsize=(12, 6))
        for ticker in TICKERS:
            if ticker in volume:
                plt.plot(volume.index, volume[ticker], label=ticker)

        plt.xlabel("Data")
        plt.ylabel("Volume de Negociação")
        plt.legend()
        plt.title("Volume de Negociação das Ações")
        plt.grid()
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        return filename
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico de volume: {e}")
        return None

def gerar_grafico_comparacao(filename):
    try:
        data = yf.download(TICKERS, period="1mo", group_by="ticker", auto_adjust=True)
        if data.empty:
            return None
        valid_tickers = [ticker for ticker in TICKERS if ticker in data.columns.get_level_values(0)]
        if not valid_tickers:
            return None

        adj_close = data.xs('Close', level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data

        normalized = adj_close / adj_close.iloc[0]

        plt.figure(figsize=(12, 6))
        for ticker in valid_tickers:
            plt.plot(normalized.index, normalized[ticker], label=ticker)

        plt.xlabel("Data")
        plt.ylabel("Preço Normalizado")
        plt.legend()
        plt.title("Comparação de Ativos")
        plt.grid()
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        return filename
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico de comparação: {e}")
        return None

def gerar_pdf(grafico_barras, grafico_precos, grafico_volume, grafico_comparacao, top_rentaveis, filename):
    try:
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter

        # Página 1: Gráfico de Barras e Gráfico de Preços
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Relatório Financeiro - Página 1")

        if grafico_barras:
            c.drawImage(grafico_barras, 50, height - 300, width=500, height=250)
        if grafico_precos:
            c.drawImage(grafico_precos, 50, height - 600, width=500, height=250)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 650, "Top 15 Ações Mais Rentáveis:")
        y_position = height - 670
        c.setFont("Helvetica", 10)
        for ticker, value in top_rentaveis.items():
            c.drawString(50, y_position, f"{ticker}: {value:.2f}%")
            y_position -= 15

        c.showPage()  
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "Relatório Financeiro - Página 2")

        if grafico_volume:
            c.drawImage(grafico_volume, 50, height - 300, width=500, height=250)
        if grafico_comparacao:
            c.drawImage(grafico_comparacao, 50, height - 600, width=500, height=250)

        c.save()
        return filename
    except Exception as e:
        logging.error(f"Erro ao gerar PDF: {e}")
        return None

async def enviar_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gerando relatório...")

    # Obter dados financeiros
    top_positive, top_negative, top_rentaveis = get_stock_data()
    if top_positive is None or top_negative is None or top_rentaveis is None:
        await update.message.reply_text("Não foi possível obter os dados financeiros.")
        return

    # Gerar gráficos
    grafico_barras = gerar_grafico_barras(top_positive, top_negative, "grafico_barras.png")
    grafico_precos = gerar_grafico_precos("grafico_precos.png")
    grafico_volume = gerar_grafico_volume("grafico_volume.png")
    grafico_comparacao = gerar_grafico_comparacao("grafico_comparacao.png")

    # Gerar PDF
    pdf_filename = "relatorio_financeiro.pdf"
    gerar_pdf(grafico_barras, grafico_precos, grafico_volume, grafico_comparacao, top_rentaveis, pdf_filename)

    # Enviar gráficos e PDF
    if grafico_barras:
        with open(grafico_barras, "rb") as chart_file:
            await update.message.reply_photo(photo=chart_file)
    if pdf_filename:
        with open(pdf_filename, "rb") as pdf_file:
            await update.message.reply_document(document=pdf_file)

    html_content = """
    <section class="container sz-small block vertical switch-to-horizontal titleCase yf-82qtw3">
        <a class="subtle-link fin-size-small titles noUnderline yf-1xqzjha" href="https://finance.yahoo.com/news/trump-delivers-on-new-tariffs-and-draws-retaliation-with-economic-toll-expected-to-be-heavy-152627780.html">...</a>
    </section>
    <section class="container sz-small block vertical switch-to-horizontal titleCase yf-82qtw3">
        <a class="subtle-link fin-size-small titles noUnderline yf-1xqzjha" href="https://finance.yahoo.com/news/live/stock-market-today-sp-500-nasdaq-dow-futures-retreat-after-trump-delivers-his-tariff-salvoes-004521286.html">...</a>
    </section>
    """
    news_urls = extract_news_urls(html_content)
    for url in news_urls:
        await update.message.reply_text(f"Principal Notícia: {url}")

    if grafico_barras:
        os.remove(grafico_barras)
    if grafico_precos:
        os.remove(grafico_precos)
    if grafico_volume:
        os.remove(grafico_volume)
    if grafico_comparacao:
        os.remove(grafico_comparacao)
    if pdf_filename:
        os.remove(pdf_filename)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bem-vindo! Aqui estão os comandos disponíveis:\n"
        "/dados - Ver dados financeiros\n"
        "/volume - Ver volume de negociação\n"
        "/relatorio - Gerar gráficos e relatório em PDF\n"
        "/addticker <TICKER> - Adicionar ação\n"
        "/removeticker <TICKER> - Remover ação\n"
        "/listtickers - Listar ações monitoradas"
    )

async def dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Obtendo dados financeiros...")

    top_positive, top_negative, top_rentaveis = get_stock_data()
    if top_positive is None or top_negative is None or top_rentaveis is None:
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

    html_content = """
    <section class="container sz-small block vertical switch-to-horizontal titleCase yf-82qtw3">
        <a class="subtle-link fin-size-small titles noUnderline yf-1xqzjha" href="https://finance.yahoo.com/news/trump-delivers-on-new-tariffs-and-draws-retaliation-with-economic-toll-expected-to-be-heavy-152627780.html">...</a>
    </section>
    <section class="container sz-small block vertical switch-to-horizontal titleCase yf-82qtw3">
        <a class="subtle-link fin-size-small titles noUnderline yf-1xqzjha" href="https://finance.yahoo.com/news/live/stock-market-today-sp-500-nasdaq-dow-futures-retreat-after-trump-delivers-his-tariff-salvoes-004521286.html">...</a>
    </section>
    """
    news_urls = extract_news_urls(html_content)
    if news_urls:
        message += "\n📰 *Principal Matéria do Motivo da Alta ou da Baixa:*\n"
        for url in news_urls:
            message += f"🔗 {url}\n"

    await update.message.reply_text(message, parse_mode="Markdown")

async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Obtendo volume de negociação...")

    volume = get_volume_data()
    if volume is None:
        await update.message.reply_text("Não foi possível obter o volume de negociação.")
        return

    message = "📊 *Volume de Negociação:*\n"
    for ticker in TICKERS:
        if ticker in volume:
            message += f"📈 {ticker}: {volume[ticker].iloc[-1]:,.0f}\n"

    await update.message.reply_text(message, parse_mode="Markdown")

async def addticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        ticker = context.args[0]
        response = add_ticker(ticker)
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Uso correto: /addticker <TICKER>")

async def removeticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        ticker = context.args[0]
        response = remove_ticker(ticker)
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Uso correto: /removeticker <TICKER>")

async def listtickers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tickers_list = ', '.join(TICKERS)
    await update.message.reply_text(f"Ações monitoradas: {tickers_list}")

def main():
    application = ApplicationBuilder().token().build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dados", dados))
    application.add_handler(CommandHandler("volume", volume))
    application.add_handler(CommandHandler("relatorio", enviar_relatorio))
    application.add_handler(CommandHandler("addticker", addticker))
    application.add_handler(CommandHandler("removeticker", removeticker))
    application.add_handler(CommandHandler("listtickers", listtickers))
    application.run_polling()

if __name__ == '__main__':
    main()