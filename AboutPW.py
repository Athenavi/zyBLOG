import bcrypt
from flask import session, flash, redirect, url_for, render_template,request
from database import get_database_connection


def zychange_password():
    if 'logged_in' not in session:
        flash('修改密码需要先登录')
        return redirect(url_for('login'))

    if 'password_confirmed' not in session or not session['password_confirmed']:
        return redirect(url_for('confirm_password'))

    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 验证用户名是否与会话中的用户名一致
        if session.get('username') != username:
            flash('请确认用户名')
            return redirect(url_for('change_password'))

        # 查询当前密码
        db = get_database_connection()
        cursor = db.cursor()
        query = "SELECT password FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchone()

        if result:
            current_password = result[0]

            # 验证新密码是否与当前密码一致
            if current_password == new_password:
                flash('新旧密码请勿一致')
                return redirect(url_for('change_password'))

            if new_password == confirm_password and len(new_password) >= 6:
                # 更新密码
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                update_query = "UPDATE users SET password = %s WHERE username = %s"
                cursor.execute(update_query, (hashed_password.decode('utf-8'), username))
                db.commit()
                cursor.close()
                db.close()

                flash('密码修改成功！')
                session.pop('logged_in', None)
                session.pop('username', None)
                session.pop('password_confirmed', None)
                return render_template('success.html')
            else:
                flash('确认密码和新密码不匹配，或者新密码长度小于6位')
        else:
            flash('信息不正确')
    return render_template('change_password.html')


def zyconfirm_password():
    if 'logged_in' not in session:
        flash('修改密码需要先登录')
        return redirect(url_for('login'))

    if 'password_confirmed' in session and session['password_confirmed']:
        return redirect(url_for('change_password'))

    if request.method == 'POST':
        password = request.form.get('password')

        # 验证密码是否正确
        db = get_database_connection()
        cursor = db.cursor()

        query = "SELECT password FROM users WHERE username = %s"
        cursor.execute(query, (session['username'],))
        result = cursor.fetchone()

        if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
            session['password_confirmed'] = True
            cursor.close()
            db.close()
            return redirect(url_for('change_password'))
        else:
            cursor.close()
            db.close()
            return render_template('confirm_password.html', error="密码错误")

    return render_template('confirm_password.html')