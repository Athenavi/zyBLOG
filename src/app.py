import base64
import configparser
import csv
import datetime
import io
import json
import logging
import os
import random
import re
import shutil
import time
import urllib
import xml.etree.ElementTree as ET
from configparser import ConfigParser

import geoip2.database
import portalocker
import requests
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, redirect, session, request, url_for, Response, jsonify, send_file, \
    make_response, send_from_directory
from flask_caching import Cache
from jinja2 import Environment, select_autoescape, FileSystemLoader
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import safe_join

from src.AboutLogin import zy_login, zy_register, get_email, profile, zy_mail_login
from src.AboutPW import zy_change_password, zy_confirm_password
from src.BlogDeal import get_article_names, get_article_content, clear_html_format, zy_get_comment, zy_post_comment, \
    get_file_date, get_blog_author, generate_random_text, read_hidden_articles, zy_send_message, auth_articles, \
    zy_show_article, zy_edit_article
from src.database import get_database_connection
from src.user import zyadmin, zy_delete_file, zy_new_article, error, get_owner_articles
from src.utils import zy_upload_file, get_user_status, get_username, get_client_ip, read_file, \
    get_weather_icon_url, zy_save_edit
from templates.custom import custom_max, custom_min

global_encoding = 'utf-8'
template_dir = 'templates'  # 模板文件的目录
loader = FileSystemLoader(template_dir)
env = Environment(loader=loader, autoescape=select_autoescape(['html', 'xml']))
env.filters['custom_max'] = custom_max
env.filters['custom_min'] = custom_min
env.add_extension('jinja2.ext.loopcontrols')

app = Flask(__name__, static_folder="../static")
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)
app.jinja_env = env
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = datetime.timedelta(hours=3)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)  # 添加 ProxyFix 中间件

# 移除默认的日志处理程序
app.logger.handlers = []

# 新增日志处理程序
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
file_handler = logging.FileHandler('temp/app.log', encoding=global_encoding)
file_handler.setFormatter(log_formatter)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

config = ConfigParser()
config.read('config.ini', encoding=global_encoding)
# 应用分享配置参数
from datetime import datetime, timedelta


@app.context_processor
def inject_variables():
    return dict(
        userStatus=get_user_status(),
        username=get_username(),
    )


@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('home'))
    else:
        return zy_login()


# 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    return zy_register()


# 登出页面
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('password_confirmed', None)
    return redirect(url_for('login'))


domain = config.get('general', 'domain').strip("'")
title = config.get('general', 'title').strip("'")


@app.route('/toggle_theme', methods=['POST'])  # 处理切换主题的请求
def toggle_theme():
    if session['theme'] == 'day-theme':
        session['theme'] = 'night-theme'  # 如果当前主题为白天，则切换为夜晚（night-theme）
    else:
        session['theme'] = 'day-theme'  # 如果当前主题为夜晚，则切换为白天（day-theme）

    return 'success'  # 返回切换成功的消息


@app.route('/search', methods=['GET', 'POST'])
def search():
    matched_content = []

    if request.method == 'POST':
        keyword = request.form.get('keyword')  # 获取搜索关键字
        cache_dir = os.path.join('temp', 'search')
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, keyword + '.xml')

        # 检查缓存是否存在且在一个小时之内
        if os.path.isfile(cache_path) and (time.time() - os.path.getmtime(cache_path) < 3600):
            # 读取缓存并继续处理
            with open(cache_path, 'r') as cache_file:
                match_data = cache_file.read()
        else:
            files = os.listdir('articles')
            markdown_files = [file for file in files if file.endswith('.md')]

            # 创建XML根元素
            root = ET.Element('root')

            for file in markdown_files:
                article_name = file[:-3]  # 移除文件扩展名 (.md)
                encoded_article_name = urllib.parse.quote(article_name)  # 对文件名进行编码处理
                article_url = domain + 'blog/' + encoded_article_name
                date = get_file_date(encoded_article_name)
                describe = get_article_content(article_name, 50)  # 建议的值50以内
                describe = clear_html_format(describe)

                if keyword.lower() in article_name.lower() or keyword.lower() in describe.lower():
                    # 创建item元素并包含内容
                    item = ET.SubElement(root, 'item')
                    ET.SubElement(item, 'title').text = article_name
                    ET.SubElement(item, 'link').text = article_url
                    ET.SubElement(item, 'pubDate').text = date
                    ET.SubElement(item, 'description').text = describe

            # 创建XML树
            tree = ET.ElementTree(root)

            # 将XML数据转换为字符串
            match_data = ET.tostring(tree.getroot(), encoding=global_encoding, method='xml').decode()

            # 写入缓存
            with open(cache_path, 'w') as cache_file:
                cache_file.write(match_data)

        # 解析XML数据
        parsed_data = ET.fromstring(match_data)
        for item in parsed_data.findall('item'):
            content = {
                'title': item.find('title').text,
                'link': item.find('link').text,
                'pubDate': item.find('pubDate').text,
                'description': item.find('description').text
            }
            matched_content.append(content)

    return render_template('search.html', results=matched_content)


def analyze_ip_location(ip_address):
    city_name = session.get('city_name')
    city_code = session.get('city_code')
    if city_name and city_code:
        return city_name,city_code
    else:
        ip_api_url = f'http://whois.pconline.com.cn/ipJson.jsp?ip={ip_address}&json=true'
        response = requests.get(ip_api_url)
        data = response.json()
        city_name = data.get('city')
        city_code = data.get('cityCode')
        session['city_name'] = city_name
        session['city_code'] = city_code
        return city_name,city_code





def check_exist(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            cache_timestamp = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - cache_timestamp <= timedelta(hours=1):
                return jsonify(cache_data)


@app.route('/weather/<city_code>', methods=['GET'])
def get_weather(city_code):
    cache_dir = 'temp'
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = os.path.join(cache_dir, f'{city_code}.json')

    # Check if cache file exists and is within one hour
    check_exist(cache_file)

    # Acquire a lock before generating cache file
    lock_file = f'{cache_file}.lock'
    try:
        with portalocker.Lock(lock_file, timeout=1) as lock:
            # Check again if cache file is created by another request
            check_exist(cache_file)
            apiUrl = f'http://t.weather.itboy.net/api/weather/city/{city_code}'
            try:
                response = requests.get(apiUrl)
                processedData = response.json()

                with open(cache_file, 'w') as f:
                    json.dump(processedData, f)

                return jsonify(processedData)
            except Exception as e:
                error_message = {'error': str(e)}
                return jsonify(error_message), 500
    except portalocker.exceptions.LockException:
        # Another request is already creating the cache file
        pass

    # If cache file creation failed, return error
    error_message = {'error': 'Failed to create cache file'}
    return jsonify(error_message), 500


@app.route('/get_city_code', methods=['POST'])
def get_city_code():
    city_name = request.form.get('city_name')
    city_name = clear_html_format(city_name)
    return zy_get_city_code(city_name)









@app.route('/profile', methods=['GET', 'POST'])
def space():
    avatar_url = profile('guest@7trees.cn')
    template = env.get_template('zyprofile.html')
    session.setdefault('theme', 'day-theme')
    notice = read_file('notice/1.txt', 50)
    userStatus = get_user_status()
    username = get_username()
    ownerArticles = None

    if userStatus and username is not None:
        ownerName = request.args.get('id')
        if ownerName is None or ownerName == '':
            ownerName = username
        ownerArticles = get_owner_articles(ownerName)
        avatar_url = get_email(ownerName)
        avatar_url = profile(avatar_url)

    if ownerArticles is None:
        ownerArticles = []  # 设置为空列表

    return template.render(url_for=url_for, theme=session['theme'],
                           notice=notice, avatar_url=avatar_url,
                           userStatus=userStatus, username=username,
                           Articles=ownerArticles)


@app.route('/settingRegion', methods=['POST'])
def setting_region():
    username = get_username()
    if username is not None:
        return 1
    return 1


@cache.cached(timeout=None, key_prefix='cities')
def get_table_data():
    db = get_database_connection()

    cursor = db.cursor()
    # 执行 MySQL 查询获取你想要缓存的表数据
    query = "SELECT * FROM cities"
    cursor.execute(query)

    # 构建数据字典列表
    data = []
    columns = [desc[0] for desc in cursor.description]
    for row in cursor.fetchall():
        data.append(dict(zip(columns, row)))

    cursor.close()
    db.close()

    return data


def zy_get_city_code(city_name):
    table_data = get_table_data()

    # 在缓存的数据中查询城市代码
    result = next((item for item in table_data if item['city_name'] == city_name), None)

    # 检查查询结果
    if result:
        return jsonify({'city_code': result['city_code']})
    else:
        return jsonify({'error': '城市不存在'})


def get_unique_tags(csv_filename):
    tags = []
    with open(csv_filename, 'r', encoding=global_encoding) as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header line
        for row in reader:
            tags.extend(row[1:])  # Append tags from the row (excluding the article name)

    unique_tags = list(set(tags))  # Remove duplicates
    return unique_tags


def get_articles_by_tag(csv_filename, tag_name):
    tag_articles = []
    with open(csv_filename, 'r', encoding=global_encoding) as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header line
        for row in reader:
            if tag_name in row[1:]:
                tag_articles.append(row[0])  # Append the article name

    return tag_articles


def get_tags_by_article(csv_filename, article_name):
    tags = []
    with open(csv_filename, 'r', encoding=global_encoding) as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header line
        for row in reader:
            if row[0] == article_name:
                tags.extend(row[1:])  # Append tags from the row (excluding the article name)
                break  # Break the loop if the article is found

    unique_tags = list(set(tags))  # Remove duplicates
    unique_tags = [tag for tag in unique_tags if tag]  # Remove empty tags
    return unique_tags


def get_list_intersection(list1, list2):
    intersection = list(set(list1) & set(list2))
    return intersection


# 主页

@app.route('/', methods=['GET', 'POST'])
def home():
    # 获取客户端IP地址
    ip = get_client_ip(request, session)
    city_name,city_code = analyze_ip_location(ip)
    if request.method == 'GET':
        page = request.args.get('page', default=1, type=int)
        tag = request.args.get('tag')

        if page <= 0:
            page = 1

        theme = session.get('theme', 'day-theme')  # 获取当前主题
        cache_key = f'page_content:{page}:{theme}:{tag}'  # 根据页面值和主题,标签生成缓存键

        # 从缓存中获取页面内容
        content = cache.get(cache_key)
        if content:
            return content

        # 重新获取页面内容
        articles, has_next_page, has_previous_page = get_article_names(page=page)
        template = env.get_template('zyhome.html')
        session.setdefault('theme', 'day-theme')
        notice = read_file('notice/1.txt', 50)
        tags = get_unique_tags('articles/tags.csv')
        if tag:
            tag_articles = get_articles_by_tag('articles/tags.csv', tag)
            articles = get_list_intersection(articles, tag_articles)

        # 获取用户名
        username = session.get('username')
        app.logger.info('当前访问的用户:{}, IP:{}, IP归属地:{},城市代码:{}'.format(username, ip, city_name,city_code))

        # 渲染模板并存储渲染后的页面内容到缓存中
        rendered_content = template.render(
            title=title, articles=articles, url_for=url_for, theme=session['theme'], IPinfo=city_name,
            notice=notice, has_next_page=has_next_page, has_previous_page=has_previous_page,
            current_page=page, city_code=city_code, username=username, tags=tags
        )
        # 将渲染后的页面内容保存到缓存，并设置过期时间
        cache.set(cache_key, rendered_content, timeout=30)
        resp = make_response(rendered_content)
        if username is None:
            username = 'qks' + format(random.randint(1000, 9999))  # 可以设置一个默认值或者抛出异常，具体根据需求进行处理

        resp.set_cookie('key', 'zyBLOG' + username, 7200)
        # 设置 cookie
        return resp

    else:
        return render_template('zyhome.html')


@app.route('/blog/<article>', methods=['GET', 'POST'])
@app.route('/blog/<article>.html', methods=['GET', 'POST'])
def blog_detail(article):
    try:
        # 根据文章名称获取相应的内容并处理
        article_name = article
        article_names = get_article_names()
        hidden_articles = read_hidden_articles()

        if article_name in hidden_articles:
            # 隐藏的文章
            return vip_blog(article_name)

        if article_name not in article_names[0]:
            return render_template('404.html'), 404

        # 通过关键字缓存内容
        @cache.cached(timeout=180, key_prefix=f"article_{article_name}")
        def get_article_content_cached():
            return get_article_content(article, 215)

        article_tags = get_tags_by_article('articles/tags.csv', article_name)
        article_content, readNav_html = get_article_content_cached()
        article_summary = clear_html_format(article_content)[:30]

        # 分页参数
        page = request.args.get('page', default=1, type=int)
        per_page = 10  # 每页显示的评论数量

        username = None
        if session.get('logged_in'):
            username = session.get('username')

        # 通过关键字缓存评论内容
        @cache.cached(timeout=180, key_prefix=f"comments_{article_name}_{username}")
        def get_comments_cached():
            if username is not None:
                return zy_get_comment(article_name, page=page, per_page=per_page)
            else:
                return None

        comments = get_comments_cached()
        article_Surl = domain + 'blog/' + article_name
        article_url = "https://api.7trees.cn/qrcode/?data=" + article_Surl
        author = get_blog_author(article_name)
        blogDate = get_file_date(article_name)
        theme = session.get('theme', 'day-theme')  # 获取当前主题

        response = make_response(render_template('BlogDetail.html', title=title, article_content=article_content,
                                                 articleName=article_name, theme=theme,
                                                 author=author, blogDate=blogDate, comments=comments,
                                                 url_for=url_for, article_url=article_url,
                                                 article_Surl=article_Surl, article_summary=article_summary,
                                                 readNav=readNav_html, article_tags=article_tags))

        # 设置服务器端缓存时间
        response.cache_control.max_age = 180
        response.expires = datetime.utcnow() + timedelta(seconds=180)

        # 设置浏览器端缓存时间
        response.headers['Cache-Control'] = 'public, max-age=180'

        return response

    except FileNotFoundError:
        return render_template('404.html'), 404


last_comment_time = {}  # 全局变量，用于记录用户最后评论时间


@app.route('/post_comment', methods=['POST'])
def post_comment():
    article_name = request.form.get('article_name')
    username = request.form.get('username')
    comment = request.form.get('comment')

    # 在处理评论前检查用户评论时间
    if username in last_comment_time:
        last_time = last_comment_time[username]
        current_time = time.time()
        if current_time - last_time < 10:
            response = {
                'result': 'error',
                'message': '请稍后再发表评论'
            }
            return json.dumps(response)

    # 更新用户最后评论时间
    last_comment_time[username] = time.time()

    # 处理评论逻辑
    result = zy_post_comment(article_name, username, comment)

    # 构建响应JSON对象
    response = {
        'result': result,
        'username': username,
        'comment': comment
    }

    return json.dumps(response)


@app.route('/sitemap.xml')
@app.route('/sitemap')
def generate_sitemap():
    cache_dir = 'temp'
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = os.path.join(cache_dir, 'sitemap.xml')

    # Check if cache file exists and is within one hour
    if os.path.exists(cache_file):
        cache_timestamp = os.path.getmtime(cache_file)
        if datetime.now().timestamp() - cache_timestamp <= 3600:
            with open(cache_file, 'r') as f:
                cached_xml_data = f.read()
            response = Response(cached_xml_data, mimetype='text/xml')
            return response

    files = os.listdir('articles')
    markdown_files = [file for file in files if file.endswith('.md')]

    # 创建XML文件头
    xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_data += '<?xml-stylesheet type="text/xsl" href="./static/sitemap.xsl"?>\n'
    xml_data += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for file in markdown_files:
        article_name = file[:-3]  # 移除文件扩展名 (.md)
        article_url = domain + 'blog/' + article_name
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

    # 写入缓存文件
    with open(cache_file, 'w') as f:
        f.write(xml_data)

    response = Response(xml_data, mimetype='text/xml')
    return response


@app.route('/feed')
@app.route('/rss')
def generate_rss():
    cache_dir = 'temp'
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = os.path.join(cache_dir, 'feed.xml')

    # Check if cache file exists and is within one hour
    if os.path.exists(cache_file):
        cache_timestamp = os.path.getmtime(cache_file)
        if datetime.now().timestamp() - cache_timestamp <= 3600:
            with open(cache_file, 'r', encoding=global_encoding, errors='ignore') as f:
                cached_xml_data = f.read()
            response = Response(cached_xml_data, mimetype='application/rss+xml')
            return response

    hidden_articles = read_hidden_articles()
    hidden_articles = [ha + ".md" for ha in hidden_articles]
    files = os.listdir('articles')
    markdown_files = [file for file in files if file.endswith('.md')]
    markdown_files = markdown_files[:10]

    # 创建XML文件头及其他信息...
    xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_data += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml_data += '<channel>\n'
    xml_data += '<title>Your RSS Feed Title</title>\n'
    xml_data += '<link>' + domain + '</link>\n'
    xml_data += '<description>Your RSS Feed Description</description>\n'
    xml_data += '<language>en-us</language>\n'
    xml_data += '<lastBuildDate>' + datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") + '</lastBuildDate>\n'
    xml_data += '<atom:link href="' + domain + 'rss" rel="self" type="application/rss+xml" />\n'

    for file in markdown_files:
        article_name = file[:-3]  # 移除文件扩展名 (.md)
        encoded_article_name = urllib.parse.quote(article_name)  # 对文件名进行编码处理
        article_url = domain + 'blog/' + encoded_article_name
        date = get_file_date(encoded_article_name)
        if file in hidden_articles:
            describe = "本文章属于加密文章"
            content = "本文章属于加密文章\n" + f'<a href="{article_url}" target="_blank" rel="noopener">带密码访问</a>'
        else:
            content, *_ = get_article_content(article_name, 10)
            describe = encoded_article_name

        # 创建item标签并包含内容
        xml_data += '<item>\n'
        xml_data += f'\t<title>{article_name}</title>\n'
        xml_data += f'\t<link>{article_url}</link>\n'
        xml_data += f'\t<guid>{article_url}</guid>\n'
        xml_data += f'\t<pubDate>{date}</pubDate>\n'
        xml_data += f'\t<description>{describe}</description>\n'
        xml_data += f'\t<content:encoded><![CDATA[{content}]]></content:encoded>'
        xml_data += '</item>\n'

    # 关闭channel和rss标签
    xml_data += '</channel>\n'
    xml_data += '</rss>\n'

    # 写入缓存文件
    with open(cache_file, 'w', encoding=global_encoding, errors='ignore') as f:
        f.write(xml_data)

    response = Response(xml_data, mimetype='application/rss+xml')
    return response


@app.route('/confirm-password', methods=['GET', 'POST'])
def confirm_password():
    return zy_confirm_password()


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    # 调用已定义的change_password函数
    return zy_change_password()


@app.route('/admin/<key>', methods=['GET', 'POST'])
def admin(key):
    return zyadmin(key)


last_newArticle_time = {}  # 全局变量，用于记录用户最后递交时间
app.config['UPLOAD_FOLDER'] = 'temp/upload'
authorMapper = configparser.ConfigParser()


@app.route('/newArticle', methods=['GET', 'POST'])
def new_article():
    if request.method == 'GET':
        username = session.get('username')
        if username in last_newArticle_time:
            last_time = last_newArticle_time[username]
            current_time = time.time()
            if current_time - last_time < 600:
                return error('您完成了一次服务（无论成功与否），此服务短期内将变得不可达，请你10分钟之后再来', 503)
        return zy_new_article()

    elif request.method == 'POST':
        username = session.get('username')
        if username in last_newArticle_time:
            last_time = last_newArticle_time[username]
            current_time = time.time()
            if current_time - last_time < 600:
                return error('距离你上次上传时间过短，请十分钟后重试', 503)

        # 更新用户最后递交时间
        last_newArticle_time[username] = time.time()
        file = request.files['file']
        if not file.filename.endswith('.md'):
            return error('Invalid file format. Only Markdown files are allowed.', 400)

        if file.content_length > 10 * 1024 * 1024:
            return error('Invalid file', 400)
        else:
            if file:
                # 保存上传的文件到指定路径
                upload_folder = os.path.join('temp/upload')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, file.filename)
                file.save(file_path)

                # 检查文件是否存在于articles文件夹下
                if os.path.isfile(os.path.join('articles', file.filename)):
                    # 如果文件已经存在，提示上传失败
                    message = '上传失败，文件已存在。'
                else:
                    # 如果文件不存在，将文件复制到articles文件夹下，并提示上传成功
                    shutil.copy(os.path.join(app.config['UPLOAD_FOLDER'], file.filename), 'articles')
                    file_name = os.path.splitext(file.filename)[0]  # 获取文件名（不包含后缀）
                    with open('articles/hidden.txt', 'a', encoding=global_encoding) as f:
                        f.write('\n' + file_name + '\n')
                    authorMapper.read('author/mapper.ini', encoding=global_encoding)
                    author_value = session.get('username')
                    # 更新 [author] 节中的键值对
                    authorMapper.set('author', file_name, f"'{author_value}'")

                    # 将更改保存到文件
                    with open('author/mapper.ini', 'w', encoding=global_encoding) as configfile:
                        authorMapper.write(configfile)

                    message = '上传成功。但目前处于隐藏状态，以便于你检查错误以及编辑'

                return render_template('postNewArticle.html', message=message)

            else:
                return redirect('/newArticle')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    return zy_upload_file()


@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    userStatus = get_user_status()
    username = get_username()
    auth = False  # 设置默认值

    if userStatus and username is not None:
        article = filename
        # Auth 认证
        auth = auth_articles(article, username)

    if auth:

        return zy_delete_file(filename)

    else:
        return error(message='您没有权限', status_code=503)


@app.route('/robots.txt')
def static_from_root():
    content = "User-agent: *\nDisallow: /admin"
    modified_content = content + '\nSitemap: ' + domain + 'sitemap.xml'  # Add your additional rule here

    response = Response(modified_content, mimetype='text/plain')
    return response


@app.route('/<path:undefined_path>')
def undefined_route(undefined_path):
    return render_template('404.html'), 404


# ...

@app.route('/generate_captcha')
def generate_captcha():
    image_base64 = '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'
    captcha_text = '8er2'
    if 'logged_in' not in session:
        return {'image': image_base64, 'captcha_text': captcha_text}
    # 生成验证码文本
    captcha_text = generate_random_text()

    # 创建一个新的图像对象
    image = Image.new('RGB', (135, 80), color=(255, 255, 255))

    # 创建字体对象并设置字体大小
    font = ImageFont.truetype('static/babyground.ttf', size=40)

    # 在图像上绘制验证码文本
    d = ImageDraw.Draw(image)
    d.text((35, 20), captcha_text, font=font, fill=(0, 0, 0))

    # 将图像转换为 RGBA 模式
    image = image.convert('RGBA')
    data = image.getdata()

    # 修改图像像素，将白色像素变为透明
    new_data = []
    theme = session.get('theme', 'day-theme')
    if theme == 'night-theme':
        new_data = data
    else:
        new_data = [(255, 255, 255, 0) if item[:3] == (255, 255, 255) else item for item in data]


    # 更新图像数据
    image.putdata(new_data)

    # 保存图像到内存中
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)

    # 将图像转换为 base64 编码字符串
    image_base64 = base64.b64encode(image_bytes.getvalue()).decode('ascii')

    # 将验证码文本存储在 session 中，用于校对
    session['captcha_text'] = captcha_text
    print(captcha_text)
    # 返回图像的 base64 编码给用户
    return {'image': image_base64, 'captcha_text': captcha_text}


@app.route('/verify_captcha', methods=['POST'])
def verify_captcha():
    # 获取前端传来的验证码值
    user_input = request.form.get('captcha')
    user_input = clear_html_format(user_input)

    # 获取存储在session中的验证码文本
    captcha_text = session['captcha_text']

    if user_input.lower() == captcha_text.lower():
        # 验证码匹配成功，执行相应逻辑
        return '验证码匹配成功'
    else:
        # 验证码匹配失败，执行相应逻辑
        return '验证码不匹配'


@app.route('/send_message', methods=['POST'])
def send_message(message):
    zy_send_message(message)
    return '1'




@app.route('/edit/<article>', methods=['GET', 'POST', 'PUT'])
def markdown_editor(article):
    if 'theme' not in session:
        session['theme'] = 'day-theme'
    # notice = read_file('notice/1.txt', 50)
    userStatus = get_user_status()
    username = get_username()
    auth = False  # 设置默认值

    if userStatus and username is not None:
        # Auth 认证
        auth = auth_articles(article, username)

    if auth:
        if request.method == 'GET':
            edit_html = zy_edit_article(article)
            show_edit = zy_show_article(article)

            tags = get_tags_by_article("articles/tags.csv", article)

            # 渲染编辑页面并将转换后的HTML传递到模板中
            return render_template('editor.html', edit_html=edit_html, show_edit=show_edit, articleName=article,
                                   theme=session['theme'], tags=tags)
        elif request.method == 'POST':
            content = request.json.get('content', '')
            show_edit = zy_show_article(content)
            return jsonify({'show_edit': show_edit})
        elif request.method == 'PUT':
            tags_input = request.get_json().get('tags')
            tags_list = []
            # 将中文逗号转换为英文逗号
            tags_input = tags_input.replace("，", ",")

            # 用正则表达式截断标签信息中超过五个标签的部分
            comma_count = tags_input.count(",")
            if comma_count > 4:
                tags_input = re.split(",{1}", tags_input, maxsplit=4)[0]

            # 限制每个标签最大字符数为10，并添加到标签列表

            for tag in tags_input.split(","):
                tag = tag.strip()
                if len(tag) <= 10:
                    tags_list.append(tag)

            # 读取标签文件，查找文章名是否存在
            exists = False
            with open('articles/tags.csv', 'r', encoding=global_encoding) as file:
                reader = csv.reader(file)
                rows = list(reader)
                for row in rows:
                    if row[0] == article:
                        row[1:] = tags_list  # 替换现有标签
                        exists = True
                        break

                # 文章名不存在，创建新行
                if not exists:
                    rows.append([article] + tags_list)

            # 写入更新后的标签文件
            with open('articles/tags.csv', 'w', encoding=global_encoding, newline='') as file:
                writer = csv.writer(file)
                writer.writerows(rows)
            return jsonify({'show_edit': "success"})

        else:
            # 渲染编辑页面
            return render_template('editor.html')

    else:
        return error(message='您没有权限', status_code=503)


@app.route('/save/edit', methods=['POST'])
def edit_save():
    content = request.json.get('content', '')
    article = request.json.get('article')

    if article is None:
        return jsonify({'message': '404'}), 404

    userStatus = get_user_status()
    username = get_username()

    if userStatus is None or username is None:
        return jsonify({'message': '您没有权限'}), 503

    # Auth 认证
    auth = auth_articles(article, username)

    if not auth:
        return jsonify({'message': '404'}), 404

    save_edit_code = zy_save_edit(article, content)
    if save_edit_code == 'success':
        return jsonify({'show_edit_code': 'success'})
    else:
        return jsonify({'show_edit_code': 'failed'})


@app.route('/hidden/article', methods=['POST'])
def hideen_article():
    article = request.json.get('article')
    if article is None:
        return jsonify({'message': '404'}), 404

    userStatus = get_user_status()
    username = get_username()

    if userStatus is None or username is None:
        return jsonify({'deal': 'noAuth'})

    auth = auth_articles(article, username)

    if not auth:
        return jsonify({'deal': 'noAuth'})

    if is_hidden(article):
        # 取消隐藏文章
        unhide_article(article)
        return jsonify({'deal': 'unhide'})
    else:
        # 隐藏文章
        hide_article(article)
        return jsonify({'deal': 'hide'})


def hide_article(article):
    with open('articles/hidden.txt', 'a', encoding=global_encoding) as hidden_file:
        # 将文章名写入hidden.txt的新的一行中
        hidden_file.write('\n' + article + '\n')


def unhide_article(article):
    with open('articles/hidden.txt', 'r', encoding=global_encoding) as hidden_file:
        hidden_articles = hidden_file.read().splitlines()

    with open('articles/hidden.txt', 'w', encoding=global_encoding) as hidden_file:
        # 从hidden中移除完全匹配文章名的一行
        for hidden_article in hidden_articles:
            if hidden_article != article:
                hidden_file.write(hidden_article + '\n')


def is_hidden(article):
    with open('articles/hidden.txt', 'r', encoding=global_encoding) as hidden_file:
        hidden_articles = hidden_file.read().splitlines()
        return article in hidden_articles


@app.route('/travel', methods=['GET'])
def travel():
    response = requests.get(domain + 'sitemap.xml')  # 发起对/sitemap接口的请求
    if response.status_code == 200:
        tree = ET.fromstring(response.content)  # 使用xml.etree.ElementTree解析响应内容

        urls = []  # 用于记录提取的URL列表
        for url_element in tree.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc_element = url_element.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_element is not None:
                urls.append(loc_element.text)  # 将标签中的内容添加到列表中

        if urls:
            random.shuffle(urls)  # 随机打乱URL列表的顺序
            random_url = urls[0]  # 选择打乱后的第一个URL
            return render_template('bh.html', jumpUrl=random_url)
        # 如果没有找到任何<loc>标签，则返回适当的错误信息或默认页面
        return "No URLs found in the response."
    else:
        # 处理无法获取响应内容的情况，例如返回错误页面或错误消息
        return "Failed to fetch sitemap content."


def vip_blog(article_name):
    userStatus = get_user_status()
    username = get_username()
    auth = False  # 设置默认值

    if userStatus and username is not None:
        # Auth 认证
        auth = auth_articles(article_name, username)

    if auth:
        if request.method == 'GET':
            article_Surl = domain + 'blog/' + article_name
            article_url = "https://api.7trees.cn/qrcode/?data=" + article_Surl
            author = get_blog_author(article_name)
            blogDate = get_file_date(article_name) + '——_______该文章处于隐藏模式(他人不可见)______——'

            # 检查session中是否存在theme键
            if 'theme' not in session:
                session['theme'] = 'day-theme'  # 如果不存在，则设置默认主题为白天（day-theme）

            article_content, readNav_html = get_article_content(article_name, 215)
            article_summary = clear_html_format(article_content)
            article_summary = article_summary[:30]

            # 分页参数
            page = request.args.get('page', default=1, type=int)
            per_page = 10  # 每页显示的评论数量

            username = None
            comments = []
            if session.get('logged_in'):
                username = session.get('username')
                if username:
                    comments = zy_get_comment(article_name, page=page, per_page=per_page)
                else:
                    comments = None
            else:
                comments = None

            if request.method == 'POST':
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify(comments=comments)  # 返回JSON响应，只包含评论数据

            return render_template('BlogDetail.html', article_content=article_content, articleName=article_name,
                                   theme=session['theme'], author=author, blogDate=blogDate, comments=comments,
                                   url_for=url_for, username=username, article_url=article_url,
                                   article_Surl=article_Surl, article_summary=article_summary, readNav=readNav_html)

        elif request.method == 'POST':
            content = request.json.get('content', '')
            show_edit = zy_show_article(content)
            return jsonify({'show_edit': show_edit})
        else:
            # 渲染编辑页面
            return zy_pw_blog(article_name)
    else:
        return zy_pw_blog(article_name)


def zy_pw_blog(article_name):
    session.setdefault('theme', 'day-theme')
    if request.method == 'GET':
        # 在此处添加密码验证的逻辑
        codePass = zy_pw_check(article_name, request.args.get('password'))
        if codePass == 'success':
            try:
                # 根据文章名称获取相应的内容并处理
                article_name = article_name
                article_Surl = domain + 'blog/' + article_name
                article_url = "https://api.7trees.cn/qrcode/?data=" + article_Surl
                author = get_blog_author(article_name)
                blogDate = get_file_date(article_name) + '文章密码已认证'

                # 检查session中是否存在theme键
                if 'theme' not in session:
                    session['theme'] = 'day-theme'  # 如果不存在，则设置默认主题为白天（day-theme）

                article_content, readNav_html = get_article_content(article_name, 215)
                article_summary = clear_html_format(article_content)
                article_summary = article_summary[:30]

                # 分页参数
                page = request.args.get('page', default=1, type=int)
                per_page = 10  # 每页显示的评论数量

                username = None
                comments = []
                if session.get('logged_in'):
                    username = session.get('username')
                    if username:
                        comments = zy_get_comment(article_name, page=page, per_page=per_page)
                    else:
                        comments = None
                else:
                    comments = None

                if request.method == 'POST':
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify(comments=comments)  # 返回JSON响应，只包含评论数据

                return render_template('hidden.html', article_content=article_content, articleName=article_name,
                                       theme=session['theme'], author=author, blogDate=blogDate, comments=comments,
                                       url_for=url_for, username=username, article_url=article_url,
                                       article_Surl=article_Surl, article_summary=article_summary, readNav=readNav_html,
                                       key="密码验证成功")

            except FileNotFoundError:
                return render_template('404.html'), 404

        else:
            return render_template('hidden.html', articleName=article_name,
                                   theme=session['theme'],
                                   url_for=url_for)


def zy_pw_check(article, code):
    try:
        invitecodes = get_invitecode_data()  # 获取invitecode表数据

        for result in invitecodes:
            if result['uuid'] == article and result['code'] == code:
                app.logger.info('完成了一次数据表更新')
                return 'success'

        return 'failed'
    except:
        return 'failed'


@cache.cached(timeout=600, key_prefix='invitecode')
def get_invitecode_data():
    db = get_database_connection()

    cursor = db.cursor()
    # 执行 MySQL 查询获取你想要缓存的表数据
    query = "SELECT * FROM invitecode"
    cursor.execute(query)

    # 构建数据字典列表
    data = []
    columns = [desc[0] for desc in cursor.description]
    for row in cursor.fetchall():
        data.append(dict(zip(columns, row)))
    current_time = datetime.now()
    app.logger.info('当前数据表更新时间：{}'.format(current_time))
    cursor.close()
    db.close()

    return data


@app.route('/change-article-pw/<filename>', methods=['POST'])
def change_article_pw(filename):
    userStatus = get_user_status()
    username = get_username()
    auth = False  # 设置默认值

    if userStatus and username is not None:
        article = filename
        # Auth 认证
        auth = auth_articles(article, username)

    if auth:
        newCode = request.get_json()['NewPass']
        article = request.get_json()["Article"]
        if newCode == '': newCode = '0000'
        return zy_change_article_pw(article, newCode)

    else:
        return error(message='您没有权限', status_code=503)


def zy_change_article_pw(filename, new_pw='1234'):
    # Connect to the database
    db = get_database_connection()

    try:
        with db.cursor() as cursor:
            # Check if the uuid exists in the table
            query = "SELECT * FROM invitecode WHERE uuid = %s"
            cursor.execute(query, (filename,))
            result = cursor.fetchone()

            if result is not None:
                # Update the code value
                query = "UPDATE invitecode SET code = %s WHERE uuid = %s"
                cursor.execute(query, (new_pw, filename))
            else:
                # Insert a new row
                # Check if the length of newCode is not greater than 4
                if len(new_pw) > 4:
                    return "failed"

                query = "INSERT INTO invitecode (uuid, code, is_used) VALUES (%s, %s, 0)"
                cursor.execute(query, (filename, new_pw))

            # Commit the changes to the database
            db.commit()

            # Return success message
            return "success"

    except Exception as e:
        # Return failure message if any error occurs
        return "failed"

    finally:
        # Close the connection and cursor
        cursor.close()
        db.close()


@app.route('/media', methods=['GET', 'POST'])
def media_space():
    type = request.args.get('type', default='img')
    page = request.args.get('page', default=1, type=int)
    userStatus = get_user_status()
    username = get_username()

    if userStatus and username is not None:
        if request.method == 'GET':
            if not type or type == 'img':
                imgs, has_next_page, has_previous_page = get_all_img(username, page=page)

                return render_template('zymedia.html', imgs=imgs, title='Media', url_for=url_for,
                                       theme=session.get('theme'), has_next_page=has_next_page,
                                       has_previous_page=has_previous_page, current_page=page, userid=username,
                                       domain=domain)
            if type == 'video':
                videos, has_next_page, has_previous_page = get_all_video(username, page=page)

                return render_template('zymedia.html', videos=videos, title='Media', url_for=url_for,
                                       theme=session.get('theme'), has_next_page=has_next_page,
                                       has_previous_page=has_previous_page, current_page=page, userid=username,
                                       domain=domain)

        elif request.method == 'POST':
            img_name = request.json.get('img_name')
            if not img_name:
                return error(message='缺少图像名称', status_code=400)

            image = get_image_path(username, img_name)
            if not image:
                return error(message='未找到图像', status_code=404)

            return image

    return error(message='您没有权限', status_code=503)


def get_media_list(username, category, page=1, per_page=10):
    files = []
    file_suffix = ()
    if category == 'img':
        file_suffix = ('.png', '.jpg', '.webp')
    elif category == 'video':
        file_suffix = ('.mp4', '.avi', '.mkv', '.webm', '.flv')
    file_dir = os.path.join('media', username)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)

    files = [file for file in os.listdir(file_dir) if file.endswith(tuple(file_suffix))]
    files = sorted(files, key=lambda x: os.path.getctime(os.path.join(file_dir, x)), reverse=True)
    total_img_count = len(files)
    total_pages = (total_img_count + per_page - 1) // per_page

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    files = files[start_index:end_index]

    has_next_page = page < total_pages
    has_previous_page = page > 1

    return files, has_next_page, has_previous_page


def get_all_img(username, page=1, per_page=10):
    imgs, has_next_page, has_previous_page = get_media_list(username, category='img')
    return imgs, has_next_page, has_previous_page


def get_all_video(username, page=1, per_page=10):
    videos, has_next_page, has_previous_page = get_media_list(username, category='video')
    return videos, has_next_page, has_previous_page


@app.route('/zyImg/<username>/<img_name>')
@app.route('/get_image_path/<username>/<img_name>')
def get_image_path(username, img_name):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_dir = os.path.join(base_dir, 'media', username)  # 修改为实际的图片目录相对路径
        img_path = os.path.join(img_dir, img_name)  # 图片完整路径

        # 从缓存中获取图像数据
        img_data = cache.get(img_path)

        # 如果缓存中没有图像数据，则从文件中读取并进行缓存
        if img_data is None:
            with open(img_path, 'rb') as f:
                img_data = f.read()
            cache.set(img_path, img_data)

        return send_file(img_path, mimetype='image/png')
    except Exception as e:
        print(f"Error in getting image path: {e}")
        return None


@app.route('/upload_image/<username1>', methods=['POST'])
def upload_image_path(username1):
    userStatus = get_user_status()
    username = get_username()
    Auth = bool(username1 == username)

    if userStatus and username is not None and Auth:
        if request.method == 'POST':
            try:
                file = None
                if 'file' in request.files:
                    file = request.files['file']

                if file is not None and file.filename.lower().endswith(
                        ('.jpg', '.png', '.webp', '.jfif', '.pjpeg', '.jpeg', '.pjp')):
                    if file.content_length > 10 * 1024 * 1024:
                        return 'Too large please use a file smaller than 10MB'
                    else:
                        if file:
                            img_dir = os.path.join('media', username)
                            os.makedirs(img_dir, exist_ok=True)

                            file_path = os.path.join(img_dir, file.filename)

                            with open(file_path, 'wb') as f:
                                f.write(file.read())

                            return 'success'
                else:
                    return 'Invalid file format. Only image files are allowed.'
            except Exception as e:
                print(f"Error in getting image path: {e}")
                return 'failed'
    else:
        return 'failed'


@app.route('/zyVideo/<username>/<video_name>')
def start_video(username, video_name):
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        video_dir = os.path.join(base_dir, 'media', username)
        video_path = os.path.join(video_dir, video_name)

        return send_file(video_path, mimetype='video/mp4', as_attachment=False, conditional=True)
    except Exception as e:
        print(f"Error in getting video path: {e}")
        return None


@app.route('/jump', methods=['GET', 'POST'])
def jump():
    url = request.args.get('url', default=domain)
    return render_template('zyJump.html', url=url, domain=domain)


@app.route('/static/<path:filename>')
def serve_static(filename):
    parts = filename.split('/')
    directory = safe_join('/'.join(parts[:-1]))
    file = parts[-1]
    return send_from_directory(directory, file)


# 彩虹聚合登录
app_id = config.get('general', 'app_id').strip("'")
app_key = config.get('general', 'app_key').strip("'")


@app.route('/login/<provider>')
def cc_login(provider):
    if provider not in ['qq', 'wx', 'alipay', 'sina', 'baidu', 'huawei', 'xiaomi', 'dingtalk']:
        return jsonify({'message': 'Invalid login provider'})

    redirect_uri = domain + "callback/" + provider

    login_url = f'https://u.cccyun.cc/connect.php?act=login&appid={app_id}&appkey={app_key}&type={provider}&redirect_uri={redirect_uri}'
    response = requests.get(login_url)
    data = response.json()
    code = data.get('code')
    if code == 0:
        cc_url = data.get('url')

    return redirect(cc_url, 302)


@app.route('/callback/<provider>')
def callback(provider):
    if provider not in ['qq', 'wx', 'alipay', 'sina', 'baidu', 'huawei', 'xiaomi', 'dingtalk']:
        return jsonify({'message': 'Invalid login provider'})

    # Replace with your app's credentials

    authorization_code = request.args.get('code')

    callback_url = f'https://u.cccyun.cc/connect.php?act=callback&appid={app_id}&appkey={app_key}&type={provider}&code={authorization_code}'

    response = requests.get(callback_url)
    data = response.json()
    code = data.get('code')
    msg = data.get('msg')
    if code == 0:
        social_uid = data.get('social_uid')
        access_token = data.get('access_token')
        nickname = data.get('nickname')
        faceimg = data.get('faceimg')
        gender = data.get('gender')
        location = data.get('location')
        ip = data.get('ip')
        session['public_ip'] = ip
        if provider == 'qq':
            user_email = social_uid + "@qq.com"
        if provider == 'wx':
            user_email = social_uid + "@wx.com"
        elif provider != 'qq' and 'wx':
            user_email = social_uid + "@qks.com"
        return zy_mail_login(user_email)


    return render_template('zylogin.html', error=msg)
