import os
import tempfile
import pytest
from app import create_app, db, UrlMap

@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + db_path,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test",
    })
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
    os.close(db_fd)
    os.unlink(db_path)

def test_shorten_and_redirect_flow(client):
    # Create a short URL
    resp = client.post("/shorten", data={"long_url": "https://example.com/path"} , follow_redirects=True)
    assert resp.status_code == 200
    # Extract code by checking DB
    with client.application.app_context():
        item = UrlMap.query.first()
        assert item is not None
        code = item.short_code

    # Redirect works
    resp2 = client.get("/" + code, follow_redirects=False)
    assert resp2.status_code == 302
    assert resp2.headers["Location"] == "https://example.com/path"

def test_custom_code_validation(client):
    # bad custom code
    resp = client.post("/shorten", data={"long_url": "https://example.com", "custom_code": "??"}, follow_redirects=True)
    assert resp.status_code == 200  # renders with flash
    # good custom code
    resp2 = client.post("/shorten", data={"long_url": "https://example.com/2", "custom_code": "my_code"}, follow_redirects=True)
    assert resp2.status_code == 200
