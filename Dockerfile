# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY manage.py ./manage.py
COPY mongo.py ./mongo.py
COPY config ./config
COPY transaction ./transaction
COPY notify ./notify 

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
