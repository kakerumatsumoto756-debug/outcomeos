FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 OUTCOMEOS_HOST=0.0.0.0 PORT=8766 OUTCOMEOS_DB=/app/data/outcomeos.sqlite3
WORKDIR /app
COPY app/ ./app/
COPY web/ ./web/
COPY main.py ./main.py
COPY requirements-cloud.txt ./requirements-cloud.txt
RUN pip install --no-cache-dir -r requirements-cloud.txt
RUN mkdir /app/data && useradd --uid 10001 --create-home outcome && chown -R outcome:outcome /app
USER outcome
EXPOSE 8766
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:'+__import__('os').getenv('PORT','8766')+'/api/health',timeout=3).read()" || exit 1
CMD ["python","main.py"]
