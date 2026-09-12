FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir google-auth==2.40.3 requests==2.32.4
COPY user_snapshot.py .
USER 65534:65534
CMD ["python", "user_snapshot.py", "--apply"]
