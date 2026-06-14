FROM python:3.11-slim

WORKDIR /app

# libraries installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
