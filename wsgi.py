from app import app, get_table_data

import socket

from database import get_database_connection, test_database_connection, CheckDatabase

if __name__ == '__main__':
    test_database_connection()
    CheckDatabase()
    table_data = get_table_data()
    table_data = bool(table_data)
    print(f"----------------数据库表 加载---------{table_data}")
    host = socket.gethostbyname(socket.gethostname())
    print(f"在浏览器中访问：http://{host}:5000/")
    print(f"在浏览器中访问：http://127.0.0.1:5000/")
    app.run(host='0.0.0.0', port=5000)