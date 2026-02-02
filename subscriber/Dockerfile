FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

# Copiar código
COPY subscriber.py .

# Ejecutar subscriber
CMD ["python", "subscriber.py"]
