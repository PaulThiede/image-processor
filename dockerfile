FROM python:3.11.5-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# requirements.txt kopieren und installieren
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# gesamten Projektordner (inkl. main.py) in /app kopieren
COPY . /app

# Befehl zum Starten der API (main.py im /app-Root)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
