
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
import qrcode

db = SQLAlchemy()

# --- Models ---
class UrlMap(db.Model):
    __tablename__ = "url_map"
    id = db.Column(db.Integer, primary_key=True)
    long_url = db.Column(db.Text, nullable=False)
    short_code = db.Column(db.String(32), unique=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    hits = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def is_expired(self) -> bool:
        return self.expires_at is not None and datetime.now(timezone.utc) > self.expires_at

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        return True
    except Exception:
        return False

# Base62 encoding
from base62 import encode_base62

def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///url_shortener.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-change-me"),
        PREFERRED_URL_SCHEME=os.getenv("PREFERRED_URL_SCHEME", "http")
    )
    if config:
        app.config.update(config)

    db.init_app(app)

    # Ensure DB exists
    with app.app_context():
        db.create_all()

    # --- Routes ---
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def index():
        # Show recent 10 links
        recent = UrlMap.query.order_by(UrlMap.created_at.desc()).limit(10).all()
        return render_template("index.html", recent=recent)

    @app.post("/shorten")
    def shorten():
        long_url = request.form.get("long_url", "").strip()
        custom_code = request.form.get("custom_code", "").strip() or None
        expires_in_days = request.form.get("expires_in", "").strip()

        # Normalize long_url: if missing scheme, try adding https://
        if long_url and not urlparse(long_url).scheme:
            long_url = "https://" + long_url

        if not is_valid_url(long_url):
            flash("Please enter a valid URL (must start with http:// or https://).", "danger")
            return redirect(url_for("index"))

        expires_at = None
        if expires_in_days:
            try:
                days = int(expires_in_days)
                if days <= 0:
                    raise ValueError
                expires_at = datetime.now(timezone.utc) + timedelta(days=days)
            except ValueError:
                flash("Expiry must be a positive integer number of days.", "danger")
                return redirect(url_for("index"))

        # Validate custom code
        if custom_code:
            if not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", custom_code):
                flash("Custom code must be 3-32 chars: letters, numbers, _ or - only.", "danger")
                return redirect(url_for("index"))
            if UrlMap.query.filter_by(short_code=custom_code).first():
                flash("That short code is already taken. Please choose another.", "danger")
                return redirect(url_for("index"))

        # Check if the same long_url already exists (reuse to avoid duplicates)
        existing = UrlMap.query.filter_by(long_url=long_url).first()
        if existing and not custom_code:
            # Update expiry if provided
            if expires_at:
                existing.expires_at = expires_at
                db.session.commit()
            short_url = request.host_url + existing.short_code
            _ensure_qr_for_code(existing.short_code, request.host_url)
            return render_template("success.html", short_url=short_url, code=existing.short_code,
                                   long_url=long_url, expires_at=existing.expires_at)

        # Create the row to get an auto-incrementing ID
        row = UrlMap(long_url=long_url, expires_at=expires_at)
        db.session.add(row)
        db.session.commit()  # to populate row.id

        # Assign short code
        code = custom_code or encode_base62(row.id)
        row.short_code = code
        db.session.commit()

        # Generate QR
        _ensure_qr_for_code(code, request.host_url)

        short_url = request.host_url + code
        return render_template("success.html", short_url=short_url, code=code,
                               long_url=long_url, expires_at=expires_at)

    def _ensure_qr_for_code(code: str, host_url: str):
        qr_folder = os.path.join(app.root_path, "static", "qr")
        os.makedirs(qr_folder, exist_ok=True)
        short_url = host_url + code
        img_path = os.path.join(qr_folder, f"{code}.png")
        if not os.path.exists(img_path):
            img = qrcode.make(short_url)
            img.save(img_path)

    @app.get("/<string:code>")
    def redirect_code(code: str):
        item = UrlMap.query.filter_by(short_code=code).first()
        if not item or item.is_expired():
            abort(404)
        item.hits = (item.hits or 0) + 1
        item.last_accessed = datetime.now(timezone.utc)
        db.session.commit()
        return redirect(item.long_url, code=302)

    @app.get("/stats/<string:code>")
    def stats(code: str):
        item = UrlMap.query.filter_by(short_code=code).first()
        if not item:
            abort(404)
        return render_template("stats.html", item=item)

    # Simple API for programmatic use
    @app.get("/api/expand/<string:code>")
    def api_expand(code: str):
        item = UrlMap.query.filter_by(short_code=code).first()
        if not item:
            return jsonify({"error": "not_found"}), 404
        return jsonify({
            "code": item.short_code,
            "long_url": item.long_url,
            "hits": item.hits,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "last_accessed": item.last_accessed.isoformat() if item.last_accessed else None,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "expired": item.is_expired(),
        })

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app

# For local dev: `python app.py`
if __name__ == "__main__":
    app = create_app()
    # Use Flask's built-in server for dev
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)
