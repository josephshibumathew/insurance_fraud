FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn python-multipart

COPY mock_api.py ./mock_api.py

EXPOSE 7860

CMD ["uvicorn", "mock_api:app", "--host", "0.0.0.0", "--port", "7860"]