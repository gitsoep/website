FROM python:3.13-alpine AS builder
RUN apk upgrade --no-cache
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-alpine
RUN apk upgrade --no-cache
WORKDIR /app
COPY --from=builder /install /usr/local
COPY main.py .
COPY templates/ templates/
COPY images/ images/
COPY static/ static/
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
