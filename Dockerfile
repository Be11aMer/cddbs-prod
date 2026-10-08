FROM python:3.11-slim

# PIP_ROOT_USER_ACTION silences the "Running pip as the 'root' user" warning:
# the image is single-purpose, so a venv adds nothing here.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONPATH=/app

WORKDIR /app
# INSTALL_DEV=true (set by docker-compose) adds pytest etc. for local dev
ARG INSTALL_DEV=false
COPY requirements.txt requirements-dev.txt /app/
RUN pip install --upgrade pip \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install -r requirements-dev.txt; \
       else pip install -r requirements.txt; fi
COPY src /app/src

# Drop root for the running process
RUN useradd --create-home --uid 1000 app
USER app

CMD ["uvicorn", "src.cddbs.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75", "--timeout-graceful-shutdown", "30"]
