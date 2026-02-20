FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv --no-cache-dir

# Copy dependency files first (layer cache optimisation)
COPY pyproject.toml ./

# Install runtime dependencies only (no dev extras in image)
RUN uv pip install --system --no-cache \
    "django>=4.2,<5.0" \
    "djangorestframework>=3.15" \
    "psycopg2-binary>=2.9" \
    "requests>=2.31" \
    "python-decouple>=3.8"

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]