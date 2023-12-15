from waitress import serve
from app import app
from database import test_database_connection, CheckDatabase

if __name__ == '__main__':
    test_database_connection()
    CheckDatabase()
    serve(app, host='0.0.0.0', port=5000)
