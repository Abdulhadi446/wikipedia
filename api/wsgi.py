from main import app
from fastapi.middleware.wsgi import WSGIMiddleware

# Wrap FastAPI app with WSGI
application = WSGIMiddleware(app)