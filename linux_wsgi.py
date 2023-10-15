from app import app
import socket
import ssl
app.config["SERVER_NAME"] = "127.0.0.1:5000"  # 设置你的服务器名称
app.config["APPLICATION_ROOT"] = "/"  # 设置你的应用程序根路径
app.config["PREFERRED_URL_SCHEME"] = "https"  #
from database import test_database_connection

if __name__ == '__main__':
    test_database_connection()
    print(f"在浏览器中访问：http://127.0.0.1:5000/")
    app.run(ssl_context=('cert.pem', 'cert.key'), port=5000)