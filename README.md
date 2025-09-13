# Zibal Backend Project

This project is a **Django + DRF** backend using **MongoDB** as the database and **Celery + Redis** for background task processing.

## 🚀 Features

- Import initial MongoDB seed data (`transaction.agz`).
- API for transaction summaries (daily/weekly/monthly).
- Management command to refresh cached transaction summaries.
- Notification system via Celery (async + retry + logging).

---

## ⚙️ Setup

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/AmiraliFarazmand/Zibal-CodingChallenge.git .
```

### 2. Make Init Script Executable

The MongoDB init script `(docker/mongo-init.sh)` must be executable:

```bash
chmod +x docker/mongo-init.sh
```

### 3. Environment Variables

Create a `.env` file in the root:

```.env
MONGO_URI="mongodb://admin:secret@mongodb:27017"
CELERY_BROKER_URL="redis://redis:6379/0"
CELERY_RESULT_BACKEND="redis://redis:6379/0"
MONGO_DB_NAME="zibal_db"
SECRET_KEY="django-insecure-8suhk)h^g#(g#&2$t1mgqu9-&r_tbhrnrkwa=al^tip+sj222sdfsdIDK"
DJANGO_SETTINGS_MODULE=config.settings
SUMMARY_TTL_SECONDS=86400
```

### 4. Start with Docker

```bash
docker compose up --build
```

### This will start:

- mongodb (seeded with initial data, runs quietly)
- redis
- api (Django server on http://localhost:8000)
- worker (Celery notifications worker)

##### p.s: I have used docker images I have already pulled, if you favor some lighter version of them you can try images wiht other tags.

## 📊 APIs

### Transaction Summary API

Endpoint:
`GET /api/v1/transactions/summary/`

Request Body Parameters :

- mode = daily | weekly | monthly
- type = count | amount
- merchantId (optional)

Response (example):

```json
[
  {"key": "1403/06/01", "value": 12},
  {"key": "1403/06/02", "value": 7},
  ...
]
```

### Transaction Summary API Using chached data

Same as previous API, but reads data from already cached colleciton

Endpoint:
`GET /api/v1/transactions/summary/chached/`

Request Body Parameters :

- mode = daily | weekly | monthly
- type = count | amount
- merchantId (optional)

Response (example):

```json
[
  {"key": "1403/06/01", "value": 12},
  {"key": "1403/06/02", "value": 7},
  ...
]
```

### Notification API

Endpoint:
`POST /api/v1/notify/reset-password`

Request body:

```json
{
  "merchantId": "abc123",
  "channel": "sms"
}
```

Response:

```json
{
  "task_id": "8f26b85c-....",
  "status": "queued"
}
```

## 🛠️ Management Command

#### You can refresh transaction summaries via a Django management command:

```bash
docker exec -it zibal_api python manage.py build_transaction_summary
```

Options:

- mode daily|weekly|monthly (default: all, can be multiple)

- merchant-id <id> (optional)

Example:
`docker exec -it zibal_api python manage.py build_transaction_summary --mode weekly monthly --merchant-id 63a69a2d18f9347bd89d5f88`

## 🔄 Celery Worker

### Celery is already wired into docker-compose as the worker service. It handles notification jobs asynchronously with retry + exponential backoff + jitter.

You can monitor logs with(beside the data it stores on DB):

```bash
docker logs -f zibal_worker
```

## 🧹 Notes

#### MongoDB data persists in the named volume zibal_mongo_data.

To reset database state:

```bash
docker compose down -v
```

MongoDB logs are quieted using `--quiet`.
