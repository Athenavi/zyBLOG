import logging
from datetime import timedelta

import bcrypt
from flask import request, session, redirect, url_for, render_template, app

from database import get_database_connection


def zylogin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_database_connection()
        cursor = db.cursor()

        try:
            query = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()

            if result is not None and bcrypt.checkpw(password.encode('utf-8'), result[2].encode('utf-8')):
                session.permanent = True  # 设置会话为永久会话
                app.permanent_session_lifetime = timedelta(minutes=120)  # 设置过期时间
                session['logged_in'] = True
                session['username'] = result[1]
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Invalid username or password")
        except Exception as e:
            logging.error(f"Error logging in: {e}")
            return "登录失败"
        finally:
            cursor.close()
            db.close()

    return render_template('login.html')


def zyregister():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        invite_code = request.form['invite_code']

        db = get_database_connection()
        cursor = db.cursor()

        try:
            # 判断用户名是否已存在
            query_username = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query_username, (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                return "该用户名已被注册，请选择其他用户名。"

            query_invite_code = "SELECT * FROM inviteCode WHERE code = %s AND is_used = FALSE"
            cursor.execute(query_invite_code, (invite_code,))
            result = cursor.fetchone()

            if result:
                # 邀请码有效，允许用户注册
                # 执行用户注册的逻辑
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

                insert_query = "INSERT INTO users (username, password) VALUES (%s, %s)"
                cursor.execute(insert_query, (username, hashed_password.decode('utf-8')))
                db.commit()

                # 将邀请码标记为已使用
                update_query = "UPDATE inviteCode SET is_used = TRUE WHERE uuid = %s"
                cursor.execute(update_query, (result[0],))
                db.commit()

                return render_template('success.html')
            else:
                return "邀请码无效或已被使用，请输入有效的邀请码。"
        except Exception as e:
            logging.error(f"Error registering user: {e}")
            return "注册失败"
        finally:
            cursor.close()
            db.close()

    return render_template('register.html')

