import mysql.connector
import configparser


def get_database_connection():
    config = configparser.ConfigParser()
    config.read('config.ini')

    db_config = dict(config.items('database'))

    db = mysql.connector.connect(
        host=db_config['host'],
        port=int(db_config['port']),  # 将端口转换为整数类型
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )
    return db
