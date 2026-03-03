FROM python:3.11-slim

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 정적 라이브러리 로컬화 (CDN 의존성 제거 — 내부망 환경 대응)
RUN apt-get update && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p static/css/fonts static/js \
    && wget -q -O static/css/bootstrap.min.css \
         https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css \
    && wget -q -O static/css/bootstrap-icons.min.css \
         https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css \
    && wget -q -O static/css/fonts/bootstrap-icons.woff2 \
         https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2 \
    && wget -q -O static/css/fonts/bootstrap-icons.woff \
         https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff \
    && wget -q -O static/js/bootstrap.bundle.min.js \
         https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js \
    && wget -q -O static/js/Sortable.min.js \
         https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js \
    && apt-get purge -y --auto-remove wget

# 앱 소스 복사
COPY app.py .
COPY parser/ ./parser/
COPY templates/ ./templates/

ENV CONFIG_DIR=/config

EXPOSE 5001

CMD ["python", "app.py"]
