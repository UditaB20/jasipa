FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Demo data is seeded only when SEED_DEMO_DATA=true; seeding resets the database.
CMD ["sh", "-c", "if [ \"$SEED_DEMO_DATA\" = \"true\" ]; then python scripts/seed_data.py; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
