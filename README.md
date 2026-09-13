# BotEconomy

Bot de Telegram para acompanhar ações: cotações, volume, relatório em PDF, alertas de preço e
resumo diário automático — tudo autossuficiente neste repositório, sem depender de nenhum serviço
externo.

> O companion de navegador (extensão Chrome/Edge) e o backend HTTP compartilhado que ele usa
> foram separados para o repositório [economy-companion](https://github.com/Igorrochalord/economy-companion).
> Este repositório contém **só o bot**, e os dois projetos não dependem um do outro.

```
.
├── bot.py               # comandos do Telegram
├── stocks.py             # dados de mercado, gráficos e geração de PDF (yfinance/matplotlib/reportlab)
├── storage.py             # persistência de tickers/alertas (data/state.json)
├── tests/
├── Dockerfile
├── docker-compose.yml
└── .env                   # config real (não versionado)
```

## 🚀 Como rodar

### Opção 1 — Docker (recomendado)

```bash
cp telegram-bot/.env.example telegram-bot/.env   # preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
docker compose up --build -d
docker compose logs -f
```

O estado (`state.json` com tickers/alertas) fica num volume nomeado (`bot_data`), sobrevive a
`docker compose down` / rebuilds.

```bash
docker compose down          # para o bot, mantém o volume de dados
docker compose down -v       # para o bot e apaga o estado salvo
docker compose up --build -d # depois de alterar código, reconstrói e sobe de novo
```

### Opção 2 — Local, sem Docker

```bash
cd telegram-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID
python bot.py
```

## Comandos

| Comando | Descrição |
|---|---|
| `/dados` | Top 10 altas, top 10 quedas e top 15 mais rentáveis do dia |
| `/volume` | Volume negociado por ticker |
| `/relatorio` | Gera e envia gráficos + relatório em PDF |
| `/addticker <TICKER>` | Adiciona uma ação à lista monitorada |
| `/removeticker <TICKER>` | Remove uma ação da lista |
| `/listtickers` | Lista as ações monitoradas |
| `/alerta <TICKER> <acima\|abaixo> <preço>` | Cria um alerta de preço |

Se `TELEGRAM_CHAT_ID` estiver configurado, o bot também agenda sozinho (via `job_queue` do
`python-telegram-bot`, fuso `America/Sao_Paulo`):
- resumo diário do mercado às `MORNING_SUMMARY_HOUR`h e `EVENING_SUMMARY_HOUR`h (padrão 6h/20h);
- checagem de alertas de preço a cada `ALERT_CHECK_MINUTES` minutos (padrão 15min), empurrando uma
  mensagem quando um alerta dispara.

Sem `TELEGRAM_CHAT_ID`, os comandos continuam funcionando normalmente — só o push automático fica
desativado.

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Obrigatório — token do bot (via [@BotFather](https://t.me/BotFather)) |
| `TELEGRAM_CHAT_ID` | Opcional — chat que recebe resumos diários e alertas de preço |
| `MORNING_SUMMARY_HOUR` / `EVENING_SUMMARY_HOUR` | Horário dos resumos diários (padrão 6/20) |
| `ALERT_CHECK_MINUTES` | Frequência de checagem dos alertas de preço (padrão 15min) |

## Testes e CI

`.github/workflows/ci.yml` roda em todo push/PR: lint (`ruff`) + testes (`pytest`), e build do
`Dockerfile` (garante que a imagem sempre builda, mesmo sem publicar).

```bash
cd telegram-bot
pip install -r requirements-dev.txt
ruff check bot.py stocks.py storage.py tests
pytest -v
```

Os testes usam um `state.json` temporário por teste (nunca tocam `telegram-bot/data/state.json`
real) e mockam o `ApplicationBuilder` do `python-telegram-bot` — não conectam no Telegram de
verdade nem no Yahoo Finance.

## Licença

MIT — ver [`LICENSE`](LICENSE).
