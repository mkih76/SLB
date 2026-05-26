FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8790

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8790", "src.app:app"]
