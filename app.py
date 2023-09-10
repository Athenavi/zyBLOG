import datetime
import logging
import os
import time
import urllib
from configparser import ConfigParser

import bcrypt
from flask import Flask, render_template, redirect, session, request, url_for, Response
from jinja2 import Environment, select_autoescape, FileSystemLoader
from werkzeug.middleware.proxy_fix import ProxyFix

from AboutLogin import zylogin, zyregister
from AboutPW import zychange_password, zyconfirm_password
from BlogDeal import get_article_names, get_article_content, clearHTMLFormat
from database import get_database_connection
from user import zyadmin

template_dir = 'templates'  # 模板文件的目录
loader = FileSystemLoader(template_dir)
env = Environment(loader=loader, autoescape=select_autoescape(['html', 'xml']))
env.add_extension('jinja2.ext.loopcontrols')

app = Flask(__name__)
app.jinja_env = env
app.secret_key = 'your_secret_key'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)  # 添加 ProxyFix 中间件

logging.basicConfig(filename='app.log', level=logging.DEBUG)

config = ConfigParser()
config.read('config.ini')


from flask import send_from_directory


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


# 登录页面


@app.route('/login', methods=['POST', 'GET'])
def login():
    return zylogin()


# 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    return zyregister()


# 登出页面
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('password_confirmed', None)
    return redirect(url_for('login'))


domain = config.get('general', 'domain')

@app.route('/toggle_theme', methods=['POST'])  # 处理切换主题的请求
def toggle_theme():
    if session['theme'] == 'day-theme':
        session['theme'] = 'night-theme'  # 如果当前主题为白天，则切换为夜晚（night-theme）
    else:
        session['theme'] = 'day-theme'  # 如果当前主题为夜晚，则切换为白天（day-theme）

    return 'success'  # 返回切换成功的消息



def read_file(file_path, num_chars):
    decoded_path = urllib.parse.unquote(file_path)  # 对文件路径进行解码处理
    encoding = 'utf-8'
    with open(decoded_path, 'r', encoding=encoding) as file:
        content = file.read(num_chars)
    return content

# 主页
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        page = request.args.get('page', default=1, type=int)  # 获取 URL 参数中的页码，默认为第一页
        articles, has_next_page, has_previous_page = get_article_names(page=page)  # 获取分页后的文章列表和翻页信息

        template = env.get_template('home.html')
        userStatu = 1 if 'logged_in' not in session else 0
        session.setdefault('theme', 'day-theme')
        notice = read_file('notice/1.txt', 50)

        return template.render(articles=articles, url_for=url_for, theme=session['theme'], userStatu=bool(userStatu),
                               notice=notice,
                               has_next_page=has_next_page, has_previous_page=has_previous_page, current_page=page)
    else:
        return render_template('home.html')


@app.route('/blog/<article>', methods=['GET'])
def blog_detail(article):
    # 根据文章名称获取相应的内容并处理
    article_name = article
    author=get_blog_author()
    blogDate=get_file_date(article_name)
    if 'theme' not in session:  # 检查session中是否存在theme键
        session['theme'] = 'day-theme'  # 如果不存在，则设置默认主题为白天（day-theme）
    article_content = get_article_content(article,215)
    return render_template('BlogDetail.html', article_content=article_content,articleName=article_name,theme=session['theme'],author=author,blogDate=blogDate)

def get_blog_author():
        articleAuthor = read_file('author/default.txt', 6)
        return articleAuthor


def get_file_date(file_path):
    decoded_name = urllib.parse.unquote(file_path)  # 对文件名进行解码处理
    file_path = os.path.join('articles', decoded_name + '.md')
    # 获取文件的创建时间
    create_time = os.path.getctime(file_path)
    # 获取文件的修改时间
    modify_time = os.path.getmtime(file_path)
    # 获取文件的访问时间
    access_time = os.path.getatime(file_path)

    formatted_modify_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(modify_time))

    return  formatted_modify_time


@app.route('/sitemap.xml')
@app.route('/sitemap')
def generate_sitemap():
    files = os.listdir('articles')
    markdown_files = [file for file in files if file.endswith('.md')]

    # 创建XML文件头
    xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_data += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for file in markdown_files:
        article_name = file[:-3]  # 移除文件扩展名 (.md)
        article_url = domain+'blog/' + article_name
        date = get_file_date(article_name)

        # 创建url标签并包含链接
        xml_data += '<url>\n'
        xml_data += f'\t<loc>{article_url}</loc>\n'
        xml_data += f'\t<lastmod>{date}</lastmod>\n'  # 添加适当的标签
        xml_data += '\t<changefreq>Monthly</changefreq>\n'  # 添加适当的标签
        xml_data += '\t<priority>0.8</priority>\n'  # 添加适当的标签
        xml_data += '</url>\n'

    # 关闭urlset标签
    xml_data += '</urlset>\n'

    response = Response(xml_data, mimetype='text/xml')

    return response



@app.route('/feed')
@app.route('/rss')
def generate_rss():
    files = os.listdir('articles')
    markdown_files = [file for file in files if file.endswith('.md')]

    # 创建XML文件头
    xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_data += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml_data += '<channel>\n'
    xml_data += '<title>Your RSS Feed Title</title>\n'
    xml_data += '<link>'+domain+'</link>\n'
    xml_data += '<description>Your RSS Feed Description</description>\n'
    xml_data += '<language>en-us</language>\n'
    xml_data += '<lastBuildDate>' + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") + '</lastBuildDate>\n'
    xml_data += '<atom:link href="'+domain+'rss" rel="self" type="application/rss+xml" />\n'

    for file in markdown_files:
        article_name = file[:-3]  # 移除文件扩展名 (.md)
        encoded_article_name = urllib.parse.quote(article_name)  # 对文件名进行编码处理
        article_url = domain+'blog/' + encoded_article_name
        date = get_file_date(encoded_article_name)
        describe = get_article_content(article_name,3)
        describe = clearHTMLFormat(describe)

        # 创建item标签并包含内容
        xml_data += '<item>\n'
        xml_data += f'\t<title>{article_name}</title>\n'
        xml_data += f'\t<link>{article_url}</link>\n'
        xml_data += f'\t<guid>{article_url}</guid>\n'
        xml_data += f'\t<pubDate>{date}</pubDate>\n'
        xml_data += f'\t<description>{describe}</description>\n'
        xml_data += '</item>\n'

    # 关闭channel和rss标签
    xml_data += '</channel>\n'
    xml_data += '</rss>\n'

    response = Response(xml_data, mimetype='application/rss+xml')

    return response



@app.route('/confirm-password', methods=['GET', 'POST'])
def confirm_password():
    return zyconfirm_password()


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    # 调用已定义的change_password函数
    return zychange_password()


@app.route('/admin/<key>', methods=['GET', 'POST'])
def admin(key):
    return zyadmin(key)

#若要安全后台入口，请使用在路由请求中移除<key> return函数back


@app.route('/<path:undefined_path>')
def undefined_route(undefined_path):
    return render_template('404.html'), 404



