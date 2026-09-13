"""Market data, charts and PDF report generation.

This is the single source of truth for financial data — both the Telegram
bot and the Chrome extension call the HTTP API built on top of these
functions instead of each re-implementing yfinance/matplotlib logic.
"""
import logging
import os
import tempfile
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from . import storage

logger = logging.getLogger(__name__)

NEWS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BotEconomy/1.0)"}


def get_stock_data(tickers: list[str] | None = None):
    tickers = tickers or storage.get_tickers()
    try:
        data = yf.download(tickers, period="2d", group_by="ticker", auto_adjust=True, progress=False)
        if data.empty:
            return None, None, None
        valid = [t for t in tickers if t in data.columns.get_level_values(0)]
        if not valid:
            return None, None, None

        adj_close = data.xs("Close", level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
        if len(adj_close) < 2:
            return None, None, None

        returns = adj_close.pct_change(fill_method=None).iloc[-1] * 100
        returns = returns.dropna()
        top_positive = returns.sort_values(ascending=False).head(10)
        top_negative = returns.sort_values().head(10)
        top_rentaveis = returns.sort_values(ascending=False).head(15)
        return top_positive, top_negative, top_rentaveis
    except Exception:
        logger.exception("Erro ao obter dados de ações")
        return None, None, None


def get_latest_prices(tickers: list[str] | None = None) -> dict[str, float]:
    """Last known close price per ticker, used for alert evaluation and quotes."""
    tickers = tickers or storage.get_tickers()
    try:
        data = yf.download(tickers, period="2d", group_by="ticker", auto_adjust=True, progress=False)
        if data.empty:
            return {}
        adj_close = data.xs("Close", level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
        last_row = adj_close.iloc[-1]
        return {t: float(last_row[t]) for t in tickers if t in last_row.index and pd.notna(last_row[t])}
    except Exception:
        logger.exception("Erro ao obter cotações")
        return {}


def get_volume_data(tickers: list[str] | None = None):
    tickers = tickers or storage.get_tickers()
    try:
        data = yf.download(tickers, period="1mo", group_by="ticker", auto_adjust=True, progress=False)
        if data.empty:
            return None
        valid = [t for t in tickers if t in data.columns.get_level_values(0)]
        if not valid:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            return data.xs("Volume", level=1, axis=1)
        return data["Volume"]
    except Exception:
        logger.exception("Erro ao obter volume")
        return None


def get_ticker_news(ticker: str, limit: int = 5) -> list[dict]:
    """Best-effort scrape of Yahoo Finance's news section for a ticker.

    Yahoo's markup changes without notice, so this always degrades to an
    empty list instead of raising — callers should treat news as optional.
    """
    url = f"https://finance.yahoo.com/quote/{ticker}/"
    try:
        resp = requests.get(url, headers=NEWS_HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for link in soup.select("a[href*='/news/']"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href:
                continue
            if href.startswith("/"):
                href = f"https://finance.yahoo.com{href}"
            items.append({"title": title, "url": href})
            if len(items) >= limit:
                break
        return items
    except Exception:
        logger.warning("Não foi possível obter notícias para %s", ticker, exc_info=True)
        return []


def gerar_grafico_barras(top_positive, top_negative, filename):
    plt.figure(figsize=(12, 6))
    bars = list(plt.bar(top_positive.index, top_positive.values, color="green", label="Top 10 em Alta"))
    bars += list(plt.bar(top_negative.index, top_negative.values, color="red", label="Top 10 em Queda"))
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2, height, f"{height:.2f}%",
            ha="center", va="bottom", fontsize=8,
        )
    plt.xlabel("Ticker")
    plt.ylabel("Variação Percentual")
    plt.title("Top 10 Ações em Alta e Queda")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    return filename


def gerar_grafico_precos(filename, tickers: list[str] | None = None):
    tickers = tickers or storage.get_tickers()
    data = yf.download(tickers, period="1mo", group_by="ticker", auto_adjust=True, progress=False)
    if data.empty:
        return None
    valid = [t for t in tickers if t in data.columns.get_level_values(0)]
    if not valid:
        return None
    adj_close = data.xs("Close", level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
    plt.figure(figsize=(12, 6))
    for ticker in valid:
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


def gerar_grafico_volume(filename, tickers: list[str] | None = None):
    tickers = tickers or storage.get_tickers()
    volume = get_volume_data(tickers)
    if volume is None:
        return None
    plt.figure(figsize=(12, 6))
    for ticker in tickers:
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


def gerar_grafico_comparacao(filename, tickers: list[str] | None = None):
    tickers = tickers or storage.get_tickers()
    data = yf.download(tickers, period="1mo", group_by="ticker", auto_adjust=True, progress=False)
    if data.empty:
        return None
    valid = [t for t in tickers if t in data.columns.get_level_values(0)]
    if not valid:
        return None
    adj_close = data.xs("Close", level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
    normalized = adj_close / adj_close.iloc[0]
    plt.figure(figsize=(12, 6))
    for ticker in valid:
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


def gerar_pdf(grafico_barras, grafico_precos, grafico_volume, grafico_comparacao, top_rentaveis, filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Relatório Financeiro - Página 1")
    if grafico_barras:
        c.drawImage(grafico_barras, 50, height - 300, width=500, height=250)
    if grafico_precos:
        c.drawImage(grafico_precos, 50, height - 600, width=500, height=250)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 650, "Top 15 Ações Mais Rentáveis:")
    y = height - 670
    c.setFont("Helvetica", 10)
    for ticker, value in top_rentaveis.items():
        c.drawString(50, y, f"{ticker}: {value:.2f}%")
        y -= 15

    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Relatório Financeiro - Página 2")
    if grafico_volume:
        c.drawImage(grafico_volume, 50, height - 300, width=500, height=250)
    if grafico_comparacao:
        c.drawImage(grafico_comparacao, 50, height - 600, width=500, height=250)

    c.save()
    return filename


def build_report_pdf(tickers: list[str] | None = None) -> str | None:
    """Generates the full PDF report in a temp dir and returns its path."""
    tickers = tickers or storage.get_tickers()
    top_positive, top_negative, top_rentaveis = get_stock_data(tickers)
    if top_positive is None:
        return None

    tmp_dir = tempfile.mkdtemp(prefix="boteconomy_")
    barras = gerar_grafico_barras(top_positive, top_negative, os.path.join(tmp_dir, "barras.png"))
    precos = gerar_grafico_precos(os.path.join(tmp_dir, "precos.png"), tickers)
    volume = gerar_grafico_volume(os.path.join(tmp_dir, "volume.png"), tickers)
    comparacao = gerar_grafico_comparacao(os.path.join(tmp_dir, "comparacao.png"), tickers)

    pdf_path = os.path.join(tmp_dir, f"relatorio_{datetime.now():%Y%m%d_%H%M%S}.pdf")
    return gerar_pdf(barras, precos, volume, comparacao, top_rentaveis, pdf_path)
