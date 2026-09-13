import logging
import os
import shutil
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from . import stocks, storage
from .config import settings
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler = start_scheduler()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="BotEconomy API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente.")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/tickers")
def list_tickers():
    return {"tickers": storage.get_tickers()}


class TickerPayload(BaseModel):
    ticker: str


@app.post("/api/tickers", dependencies=[Depends(require_api_key)])
def create_ticker(payload: TickerPayload):
    ok, message = storage.add_ticker(payload.ticker)
    if not ok:
        raise HTTPException(status_code=409, detail=message)
    return {"message": message, "tickers": storage.get_tickers()}


@app.delete("/api/tickers/{ticker}", dependencies=[Depends(require_api_key)])
def delete_ticker(ticker: str):
    ok, message = storage.remove_ticker(ticker)
    if not ok:
        raise HTTPException(status_code=404, detail=message)
    return {"message": message, "tickers": storage.get_tickers()}


@app.get("/api/summary")
def summary():
    top_positive, top_negative, top_rentaveis = stocks.get_stock_data()
    if top_positive is None:
        raise HTTPException(status_code=502, detail="Não foi possível obter os dados financeiros.")
    return {
        "top_positive": top_positive.round(2).to_dict(),
        "top_negative": top_negative.round(2).to_dict(),
        "top_rentaveis": top_rentaveis.round(2).to_dict(),
    }


@app.get("/api/volume")
def volume():
    data = stocks.get_volume_data()
    if data is None:
        raise HTTPException(status_code=502, detail="Não foi possível obter o volume de negociação.")
    latest = data.iloc[-1]
    return {
        "volume": {
            t: int(latest[t])
            for t in storage.get_tickers()
            if t in latest.index and pd.notna(latest[t])
        }
    }


@app.get("/api/quote/{ticker}")
def quote(ticker: str):
    prices = stocks.get_latest_prices([ticker.upper()])
    if ticker.upper() not in prices:
        raise HTTPException(status_code=404, detail="Ticker não encontrado ou sem dados.")
    return {"ticker": ticker.upper(), "price": prices[ticker.upper()]}


@app.get("/api/news")
def news(ticker: str):
    return {"ticker": ticker.upper(), "items": stocks.get_ticker_news(ticker.upper())}


@app.get("/api/alerts")
def list_alerts():
    return {"alerts": storage.get_alerts()}


class AlertPayload(BaseModel):
    ticker: str
    condition: str  # "above" | "below"
    price: float


@app.post("/api/alerts", dependencies=[Depends(require_api_key)])
def create_alert(payload: AlertPayload):
    if payload.condition not in ("above", "below"):
        raise HTTPException(status_code=400, detail="condition deve ser 'above' ou 'below'.")
    alert = storage.add_alert(payload.ticker, payload.condition, payload.price)
    return {"alert": alert}


@app.delete("/api/alerts/{alert_id}", dependencies=[Depends(require_api_key)])
def delete_alert(alert_id: int):
    if not storage.remove_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    return {"message": "Alerta removido."}


@app.get("/api/report")
def report():
    pdf_path = stocks.build_report_pdf()
    if not pdf_path:
        raise HTTPException(status_code=502, detail="Não foi possível gerar o relatório.")
    cleanup = BackgroundTask(shutil.rmtree, os.path.dirname(pdf_path), ignore_errors=True)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path),
        background=cleanup,
    )
