FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY worker.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "worker.py"]

