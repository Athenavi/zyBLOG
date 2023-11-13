import mysql.connector
import configparser


def get_database_connection():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    db_config = dict(config.items('database'))

    db = mysql.connector.connect(
        host=db_config['host'].strip("'"),
        port=int(db_config['port'].strip("'")),  # 将端口转换为整数类型，并去除单引号
        user=db_config['user'].strip("'"),
        password=db_config['password'].strip("'"),
        database=db_config['database'].strip("'")
    )
    return db

def test_database_connection():
    try:
        db = get_database_connection()
        db.close()
        print("Database connection is successful.")
    except mysql.connector.Error as err:
        print(f"Failed to connect to the database: {err}")


def CheckDatabase():
    try:
        db = get_database_connection()
        cursor = db.cursor()

        # 执行查询
        sql = "SHOW TABLES"  # 查询所有表的SQL语句
        cursor.execute(sql)
        result = cursor.fetchall()

        # 检查查询结果
        if result:
            for row in result:
                print(row[0], end="/")
            print(f"Total tables: {len(result)}")
            print(f"----------------数据库表 预检测---------success")
        else:
            print("No tables found in the database.")
            print(f"----------------数据库表丢失")
            return 0

    finally:
        # 关闭数据库连接
        cursor.close()
        db.close()

    return len(result)
