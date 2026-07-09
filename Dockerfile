FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    TRADING_GAME_DB=/app/data/trading_game.db \
    TRADING_GAME_HOST=0.0.0.0 \
    TRADING_GAME_PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data \
    && useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
