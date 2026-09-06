FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

COPY webapp/requirements.txt /srv/requirements.txt
RUN pip install -r /srv/requirements.txt

# data/portfolio.json is read at startup, so it has to come along
COPY data/ /srv/data/
COPY webapp/app/ /srv/webapp/app/
COPY webapp/static/ /srv/webapp/static/

WORKDIR /srv/webapp
EXPOSE 8000

# Container hosts hand you $PORT; default to 8000 when they don't.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s \
  CMD python -c "import urllib.request,os,sys; \
    sys.exit(0 if urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8000')}/api/health\", timeout=8).status==200 else 1)"
