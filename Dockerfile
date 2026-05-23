FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN DJANGO_SETTINGS_MODULE=sheglow.settings.prod \
    SECRET_KEY=build-placeholder \
    DATABASE_URL=sqlite:///tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "sheglow.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
