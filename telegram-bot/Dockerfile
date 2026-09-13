FROM python:3.12-slim

WORKDIR /app

# libgomp1: required by numpy/pandas wheels at runtime on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py stocks.py storage.py ./

CMD ["python", "bot.py"]
