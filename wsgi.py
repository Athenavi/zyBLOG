from waitress import serve
from src.app import app
from src.database import test_database_connection, CheckDatabase
from werkzeug.middleware.proxy_fix import ProxyFix

if __name__ == '__main__':
    test_database_connection()
    CheckDatabase()
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)
    print(f"从浏览器打开: http://127.0.0.1:5000")
    serve(app, host='0.0.0.0', port=5000)