from app import app

#import socket

from database import test_database_connection, CheckDatabase

if __name__ == '__main__':
    test_database_connection()
    CheckDatabase()
    #host = socket.gethostbyname(socket.gethostname())
    #print(f"在浏览器中访问：http://{host}:5000/")
    #print(f"在浏览器中访问：http://127.0.0.1:5000/")
    app.run(host='0.0.0.0', port=5000)