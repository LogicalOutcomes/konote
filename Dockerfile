FROM python:3.12-slim

# Security: run as non-root user
RUN groupadd -r konote && useradd -r -g konote konote

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files (errors shown for debugging)
RUN FIELD_ENCRYPTION_KEY=dummy-build-key SECRET_KEY=dummy-build-key ALLOWED_HOSTS=* python manage.py collectstatic --noinput --settings=konote.settings.production

# Switch to non-root user
USER konote

EXPOSE 8000

CMD ["gunicorn", "konote.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
