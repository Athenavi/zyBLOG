from datetime import datetime

from flask import render_template

from database import get_database_connection
from utils import generate_short_url


# 专属
def create_special_url(long_url, username):
    db = get_database_connection()
    cursor = db.cursor()

    try:
        query = "SELECT short_url FROM urls WHERE long_url = %s AND username = %s"
        cursor.execute(query, (long_url, username))
        result = cursor.fetchone()

        if result:
            short_url = result[0]
        else:
            short_url = generate_short_url()

            insert_query = "INSERT INTO urls (long_url, short_url, username) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (long_url, short_url, username))
            db.commit()

        return short_url
    except Exception:
        return render_template('404.html', error="Page Not Found")
    finally:
        cursor.close()
        db.close()


def redirect_to_long_url(short_url):
    db = get_database_connection()
    cursor = db.cursor()

    try:
        query = "SELECT long_url FROM urls WHERE short_url = %s"
        cursor.execute(query, (short_url,))
        result = cursor.fetchone()

        if result:
            long_url = result[0]

            insert_query = "INSERT INTO opentimes (short_url, response_count, first_response_time) VALUES (%s, %s, %s)"
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(insert_query, (short_url, 1, current_time))
            db.commit()

            return long_url
        else:
            return render_template('404.html', error="Page Not Found")
    except Exception:
        return render_template('404.html', error="Page Not Found")
    finally:
        cursor.close()
        db.close()


def delete_link(short_url):
    db = get_database_connection()
    cursor = db.cursor()

    try:
        query = "DELETE FROM urls WHERE short_url = %s"
        cursor.execute(query, (short_url,))
        db.commit()

        return True
    except Exception:
        return render_template('404.html', error="Page Not Found")
    finally:
        cursor.close()
        db.close()


def get_link_info(username):
    db = get_database_connection()
    cursor = db.cursor()

    # 查询用户是否为管理员
    query_admin = "SELECT ifAdmin FROM users WHERE username = %s"
    cursor.execute(query_admin, (username,))
    admin_result = cursor.fetchone()

    # 如果用户是管理员，则查询所有链接信息
    if admin_result and admin_result[0] == 1:
        query = "SELECT created_at, short_url, long_url FROM urls"
        cursor.execute(query)
    else:
        # 否则，查询特定用户的链接信息
        query = "SELECT created_at, short_url, long_url FROM urls WHERE username = %s"
        cursor.execute(query, (username,))

    result = cursor.fetchall()

    cursor.close()
    db.close()

    return result
