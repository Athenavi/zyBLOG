import mysql.connector
import configparser


def get_database_connection():
    config = configparser.ConfigParser()
    config.read('config.ini')

    db_config = dict(config.items('database'))

    db = mysql.connector.connect(
        host=db_config['host'].strip("'"),
        port=int(db_config['port'].strip("'")),  # 将端口转换为整数类型，并去除单引号
        user=db_config['user'].strip("'"),
        password=db_config['password'].strip("'"),
        database=db_config['database'].strip("'")
    )
    return db