# PyShort — Flask URL Shortener

A clean, production-ready Flask URL shortener with a web interface, QR codes, and basic analytics.

## Features

- Shorten links with auto-generated or custom aliases (`/abc123` or `/my-code`)
- Web UI (Bootstrap 5) + copy button + QR code image
- Redirects with click tracking + last accessed timestamp
- Optional link expiry in days
- Recent links panel
- Simple JSON API to expand short codes
- SQLite by default; configurable with `DATABASE_URL`
- Dockerfile + Gunicorn for production
- Pytest tests

## Quickstart (Local)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python app.py  # runs on http://127.0.0.1:5000
```

Open http://127.0.0.1:5000 in your browser.

## Quickstart (Docker)

```bash
docker build -t pyshort .
docker run --rm -p 8000:8000 pyshort
```
Open http://127.0.0.1:8000

## Configuration

- `DATABASE_URL`: SQLAlchemy DB URI. Defaults to `sqlite:///url_shortener.db`
- `SECRET_KEY`: Flask session key (set a strong value in prod)
- `PREFERRED_URL_SCHEME`: `http` or `https` (affects generated absolute URLs)

## API

- `GET /api/expand/<code>` → returns JSON with long URL and stats
- `GET /stats/<code>` → HTML stats page

## Tests

```bash
pytest -q
```

## Project Structure

```
url-shortener-flask/
  app.py
  base62.py
  requirements.txt
  Dockerfile
  templates/
    base.html
    index.html
    success.html
    stats.html
    404.html
  static/
    style.css
    qr/  # generated QR images
  tests/
    test_app.py
```

## Notes

- This demo stores QR images under `static/qr/`. You can serve them via CDN or object storage in production.
- For custom domains, front this app with Nginx/Caddy and a reverse proxy (TLS).
- For rate-limiting, add `Flask-Limiter`.
