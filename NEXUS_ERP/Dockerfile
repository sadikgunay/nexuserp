FROM python:3.9-slim

WORKDIR /app

# Sistem bağımlılıkları (Postgres ve Resim işleme için)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gunicorn ile başlat
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]