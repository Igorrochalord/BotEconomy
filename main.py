logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TICKERS = []

def get_stock_data():
    try:
        data = yf.download(TICKERS, period="2d", group_by="ticker", auto_adjust=True)
        if data.empty:
            return None, None

        adj_close = data.xs('Close', level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
        if len(adj_close) < 2:
            return None, None

        returns = adj_close.pct_change().iloc[-1] * 100
        top_positive = returns.sort_values(ascending=False).head(5)
        top_negative = returns.sort_values().head(5)
        return top_positive, top_negative
    except Exception as e:
        logging.error(f"Erro ao obter dados: {e}")
        return None, None

def generate_chart(top_positive, top_negative, filename='chart.png'):
    combined = pd.concat([top_positive, top_negative])
    plt.figure(figsize=(10, 6))
    colors = ['green' if x >= 0 else 'red' for x in combined.values]
    bars = plt.bar(combined.index, combined.values, color=colors)
    plt.xlabel('Ticker')
    plt.ylabel('Variação (%)')
    plt.title('Desempenho das Ações')

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.2f}%', ha='center', va='bottom')

    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def get_volume_data():
    try:
        data = yf.download(TICKERS, period="5d", group_by="ticker", auto_adjust=True)
        if data.empty:
            return None

        volume_data = data.xs('Volume', level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data['Volume']
        avg_volume = volume_data.mean()
        return avg_volume
    except Exception as e:
        logging.error(f"Erro ao obter dados de volume: {e}")
        return None
def generate_pdf_report(top_positive, top_negative, volume_data, chart_path, pdf_filename='report.pdf'):
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "Relatório de Ações")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 100, "Top Ações em Alta:")
    c.setFont("Helvetica", 12)
    y = height - 120
    for ticker, change in top_positive.items():
        c.drawString(60, y, f"📈 {ticker}: {change:.2f}%")
        y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, height - 100, "Top Ações em Queda:")
    c.setFont("Helvetica", 12)
    y_temp = height - 120
    for ticker, change in top_negative.items():
        c.drawString(310, y_temp, f"📉 {ticker}: {change:.2f}%")
        y_temp -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_temp - 40, "Resumo do Volume (Últimas 5 Sessões):")
    c.setFont("Helvetica", 12)
    y_temp -= 60
    if volume_data is not None:
        for ticker, volume in volume_data.items():
            c.drawString(60, y_temp, f"📊 {ticker}: {volume:.2f}")
            y_temp -= 20
    else:
        c.drawString(60, y_temp, "Dados de volume não disponíveis.")
        y_temp -= 20

    try:
        c.drawImage(chart_path, 50, y_temp - 250, width=500, height=250)
    except Exception as e:
        c.drawString(50, y_temp - 20, f"Erro ao carregar gráfico: {e}")
    c.save()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bem-vindo! Use o comando /dados para obter os dados financeiros.")

async def dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Obtendo dados financeiros...")
    top_positive, top_negative = get_stock_data()
    if top_positive is None:
        await update.message.reply_text("Não foi possível obter os dados do mercado.")
        return

    volume_data = get_volume_data()

    response_text = "Top Ações em Alta:\n"
    for ticker, change in top_positive.items():
        response_text += f"📈 {ticker}: {change:.2f}%\n"
    response_text += "\nTop Ações em Queda:\n"
    for ticker, change in top_negative.items():
        response_text += f"📉 {ticker}: {change:.2f}%\n"
    if volume_data is not None:
        response_text += "\nMédia de Volume Negociado (Últimas 5 Sessões):\n"
        for ticker, volume in volume_data.items():
            response_text += f"📊 {ticker}: {volume:.2f}\n"
    else:
        response_text += "\nDados de volume não disponíveis.\n"

    await update.message.reply_text(response_text)

    chart_filename = "chart.png"
    pdf_filename = "report.pdf"
    generate_chart(top_positive, top_negative, chart_filename)
    generate_pdf_report(top_positive, top_negative, volume_data, chart_filename, pdf_filename)

    with open(chart_filename, "rb") as chart_file:
        await update.message.reply_photo(photo=chart_file)
    with open(pdf_filename, "rb") as pdf_file:
        await update.message.reply_document(document=pdf_file)

    os.remove(chart_filename)
    os.remove(pdf_filename)

# Comando /volume
async def volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Calculando média de volume negociado...")
    avg_volume = get_volume_data()
    if avg_volume is None:
        await update.message.reply_text("Não foi possível obter os dados de volume.")
        return

    response_text = "Média de Volume Negociado (Últimas 5 Sessões):\n"
    for ticker, volume in avg_volume.items():
        response_text += f"📊 {ticker}: {volume:.2f}\n"

    await update.message.reply_text(response_text)

async def check_market_close(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(pytz.timezone("America/New_York"))  
    market_close_time = time(16, 0)  

    if now.time() >= market_close_time:
        await context.bot.send_message(chat_id=context.job.chat_id, text="O mercado fechou por hoje. 🛑")

# Função principal
def main():
    application = ApplicationBuilder().token().build()
    job_queue = application.job_queue
    job_queue.run_daily(check_market_close, time=time(16, 0, tzinfo=pytz.timezone("America/New_York")), days=(0, 1, 2, 3, 4))

    application.run_polling()

if __name__ == '__main__':
    main()