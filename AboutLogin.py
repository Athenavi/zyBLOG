import configparser
import logging
import random
from datetime import timedelta

import bcrypt
import bleach  # 导入 bleach 库用于 XSS 防范
from flask import request, session, redirect, url_for, render_template, app

from database import get_database_connection


def zylogin():
    if request.method == 'POST':
        input_value = bleach.clean(request.form['username'])  # 用户输入的用户名或邮箱
        password = bleach.clean(request.form['password'])

        if input_value == 'guest@7trees.cn':
            return render_template('login.html', error="Guest account cannot be used for login")

        db = get_database_connection()
        cursor = db.cursor()

        try:
            query = "SELECT * FROM users WHERE (username = %s OR email = %s) AND username <> 'guest@7trees.cn'"
            cursor.execute(query, (input_value, input_value))
            result = cursor.fetchone()

            if result is not None and bcrypt.checkpw(password.encode('utf-8'), result[2].encode('utf-8')):
                session.permanent = True
                app.permanent_session_lifetime = timedelta(minutes=120)
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

    return render_template('login.html', title="登录")


def zyregister():
    if request.method == 'POST':
        username = bleach.clean(request.form['username'])  # 使用 bleach 进行 XSS 防范
        password = bleach.clean(request.form['password'])
        invite_code = bleach.clean(request.form['invite_code'])

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
                cursor.execute(insert_query, (username, hashed_password))
                db.commit()

                # 将邀请码标记为已使用
                update_query = "UPDATE inviteCode SET is_used = TRUE WHERE uuid = %s"
                cursor.execute(update_query, (result[0],))
                db.commit()
                session.pop('logged_in', None)
                session.pop('username', None)
                session.pop('password_confirmed', None)
                return render_template('success.html')
            else:
                return "邀请码无效或已被使用，请输入有效的邀请码。"
        except Exception as e:
            logging.error(f"Error registering user: {e}")
            return "注册失败"
        finally:
            cursor.close()
            db.close()

    return render_template('register.html', title="注册新用户")

def get_email(username):
    email = 'guest@7trees.cn'
    if username is not None and isinstance(username, str):
        username = bleach.clean(username)
    db = get_database_connection()
    cursor = db.cursor()

    try:
        query = "SELECT email FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchone()  # 获取查询结果

        if result:
            email = result[0]  # 从结果中提取email值

    finally:
        cursor.close()
        db.close()

    return email

import hashlib
def profile(email):
    email = email  # 用户的电子邮件地址
    # 将电子邮件地址转换为小写，并使用 MD5 哈希算法生成哈希值
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    # 构建 Gravatar 头像的 URL
    avatar_url = f'https://www.gravatar.com/avatar/{email_hash}?s=100&r=g&d=retro'

    return avatar_url

def zyMaillogin(user_email):
    username = 'qks' + format(random.randint(1000, 9999))
    password = '123456'
    db = get_database_connection()
    cursor = db.cursor()

    try:
        # 判断用户是否已存在
        query = "SELECT * FROM users WHERE (username = %s OR email = %s) AND username <> 'guest@7trees.cn'"
        cursor.execute(query, (user_email, user_email))
        result = cursor.fetchone()

        if result is not None:
            session.permanent = True
            app.permanent_session_lifetime = timedelta(minutes=120)
            session['logged_in'] = True
            session['username'] = result[1]

            return render_template('success.html', message="授权通过!你可以关闭此页面")

        else:
            # 执行用户注册的逻辑
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            insert_query = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (username, hashed_password, user_email))
            db.commit()
            message = '已经为您自动注册账号\n' + '账号' + username + '默认密码：123456 请尽快修改'
            return render_template('success.html', message=message)

    except Exception as e:
        logging.error(f"Error registering user: {e}")
        return "注册失败,如遇到其他问题，请尽快反馈"

    finally:
        cursor.close()
        db.close()


import smtplib
from email.mime.text import MIMEText
from email.header import Header

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')
mail_config = dict(config.items('mail'))
mail_host=mail_config['host']
mail_port=mail_config['port']
mail_user=mail_config['user']
mail_password=mail_config['password']
mail_title=mail_config['title']


def zySendMail(code, toMail):
    # 发件人邮箱地址和密码
    smtp_server = mail_host
    smtp_port = mail_port
    sender_email = mail_user  # 这里替换为您自己的发件人邮箱地址
    sender_password = mail_password  # 这里是你的授权码？ 非邮箱登录密码

    # 收件人邮箱地址
    recipient_email = str(toMail)

    # 创建一封邮件，文本内容为 "Hello, World!"
    message = MIMEText('您的验证码为'+code+"请勿泄露", 'plain', 'utf-8')
    message['From'] = Header('发件人昵称 <{}>'.format(sender_email), 'utf-8')  # 设置发件人昵称
    message['To'] = Header('收件人昵称 <{}>'.format(recipient_email), 'utf-8')  # 设置收件人昵称
    message['Subject'] = Header('邮件主题', 'utf-8')  # 设置邮件主题

    try:
        # 连接邮件服务器并登录
        smtp_connection = smtplib.SMTP(smtp_server, smtp_port)
        smtp_connection.login(sender_email, sender_password)

        # 发送邮件
        smtp_connection.sendmail(sender_email, recipient_email, message.as_string())

        # 关闭连接
        smtp_connection.quit()

        print("邮件发送成功！")

    except Exception as e:
        print("邮件发送失败：", e)
