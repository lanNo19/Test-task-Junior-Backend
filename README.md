# Instagram Sync Service

A Django + DRF service that synchronises Instagram media into a local PostgreSQL database and proxies comment creation back to Instagram.

## Architecture Overview

```
posts/
├── clients/instagram.py   ← InstagramClient: all HTTP to Instagram, deep module
├── services/sync.py       ← SyncService: orchestrates full media sync
├── services/comment.py    ← CommentService: posts + persists comments
├── views.py               ← HTTP layer: parse → service → serialize
├── models.py              ← Post, Comment
├── serializers.py
├── pagination.py
└── tests/                 ← Integration + unit + property-based tests
```

No Instagram API calls ever appear in views or serializers. All outbound HTTP is abstracted away into `InstagramClient`.

---

## Quick Start (Docker)

```bash
# 1. Clone your fork
git clone https://github.com/lanNo19/Test-task-Junior-Backend.git
cd Test-task-Junior-Backend.git

# 2. Configure environment
cp .env.example .env
# Edit .env and set:
#   INSTAGRAM_ACCESS_TOKEN=...
#   INSTAGRAM_USER_ID=...
#   SECRET_KEY=...

# 3. Start everything
docker-compose up --build
```

The API is available at `http://localhost:8000/api/`.

---

## uv + PyCharm

```bash
# Install uv
pip install uv

# Create venv and install all dependencies
uv venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Copy and fill in env vars
cp .env.example .env

# Run migrations (requires PostgreSQL running locally)
python manage.py migrate

# Start dev server
python manage.py runserver
```

---

## Getting Your Instagram Access Token

1. Go to [Meta for Developers](https://developers.facebook.com/apps/) and create an app.
2. Add the **Instagram** product to your app.
3. Follow [Get Started with Instagram API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started).
4. Generate a token directly in the App Dashboard — **no OAuth flow required**.
5. Copy the token and your numeric User ID into `.env`.

---

## API Reference

### `POST /api/sync/`

Fetches all media from Instagram and upserts into local DB.

```bash
curl -X POST http://localhost:8000/api/sync/
```

```json
{ "created": 12, "updated": 3 }
```

| Status | Meaning |
|--------|---------|
| 200 | Sync completed |
| 502 | Instagram API error |

---

### `GET /api/posts/`

Returns locally cached posts with cursor pagination.

```bash
curl http://localhost:8000/api/posts/
curl "http://localhost:8000/api/posts/?cursor=<cursor>"
```

```json
{
  "next": "http://localhost:8000/api/posts/?cursor=cD0y",
  "previous": null,
  "results": [
    {
      "id": 1,
      "instagram_id": "17854360229135492",
      "caption": "Hello world",
      "media_type": "IMAGE",
      "media_url": "https://...",
      "permalink": "https://www.instagram.com/p/",
      "timestamp": "2024-11-01T10:00:00Z",
      "synced_at": "2025-02-13T12:00:00Z"
    }
  ]
}
```

---

### `POST /api/posts/{id}/comment/`

Posts a comment to Instagram and saves it locally. `{id}` is the **internal** DB primary key.

```bash
curl -X POST http://localhost:8000/api/posts/1/comment/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Great shot!"}'
```

```json
{
  "id": 7,
  "post": 1,
  "instagram_comment_id": "17858893269000001",
  "text": "Great shot!",
  "created_at": "2025-02-13T12:05:00Z"
}
```

| Status | Meaning |
|--------|---------|
| 201 | Comment created |
| 400 | Invalid request body |
| 404 | Post not found in local DB |
| 502 | Instagram rejected the comment |

---

## Running Tests

```bash
# All tests
python -m pytest

# Specific test file
python -m pytest posts/tests/test_comment_endpoint.py -v

# With coverage
python -m pytest --cov=posts --cov-report=term-missing

# Property-based tests only
python -m pytest posts/tests/test_comment_properties.py -v
```

Tests run fully offline, no real Instagram API calls are made. All HTTP is mocked.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `INSTAGRAM_ACCESS_TOKEN` | Yes | Long-lived Graph API token |
| `INSTAGRAM_USER_ID` | Yes | Numeric Instagram user ID |
| `INSTAGRAM_API_VERSION` | No | API version (default: `v21.0`) |
| `SECRET_KEY` | Yes (prod) | Django secret key |
| `DEBUG` | No | `True` for development |
| `DATABASE_URL` | No | Overrides default DB config |