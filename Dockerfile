FROM python:3.11-slim

# python
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

WORKDIR /app
COPY . .