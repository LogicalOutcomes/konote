FROM python:3.12-slim

# UTF-8 locale — required for French .mo translation files
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

# Security: run as non-root user
RUN groupadd -r konote && useradd -r -g konote -m konote

WORKDIR /app

# WeasyPrint system dependencies (PDF export)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files (uses konote.settings.build - no env vars needed)
RUN python manage.py collectstatic --noinput --settings=konote.settings.build

# Make entrypoint executable and create fontconfig cache dir for non-root user
RUN chmod +x /app/entrypoint.sh && mkdir -p /home/konote/.cache/fontconfig && chown -R konote:konote /home/konote

# Switch to non-root user
USER konote

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
