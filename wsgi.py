from waitress import serve
from app import app
from database import test_database_connection, CheckDatabase
from werkzeug.middleware.proxy_fix import ProxyFix

if __name__ == '__main__':
    test_database_connection()
    CheckDatabase()
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)
    serve(app, host='0.0.0.0', port=5000)