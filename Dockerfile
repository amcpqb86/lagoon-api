FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    libgeos-dev \
    libproj-dev \
    proj-data \
    proj-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5050

CMD ["gunicorn", "-w", "1", "--threads", "2", "-b", "0.0.0.0:5050", "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5", "--preload", "app:app"]

HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5050/', timeout=3)"