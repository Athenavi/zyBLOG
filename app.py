import datetime
import logging
import os
import time
import urllib
from configparser import ConfigParser

import requests
from flask import Flask, render_template, redirect, session, request, url_for, Response, jsonify
from jinja2 import Environment, select_autoescape, FileSystemLoader
from werkzeug.middleware.proxy_fix import ProxyFix

from AboutLogin import zylogin, zyregister, get_email
from AboutPW import zychange_password, zyconfirm_password
from BlogDeal import get_article_names, get_article_content, clearHTMLFormat, zy_get_comment, zy_post_comment
from user import zyadmin, zy_delete_file
from utils import zy_upload_file
import feedparser

template_dir = 'templates'  # 模板文件的目录
loader = FileSystemLoader(template_dir)
env = Environment(loader=loader, autoescape=select_autoescape(['html', 'xml']))
env.add_extension('jinja2.ext.loopcontrols')




app = Flask(__name__)

app.jinja_env = env
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = datetime.timedelta(hours=3)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)  # 添加 ProxyFix 中间件

logging.basicConfig(filename='app.log', level=logging.DEBUG)

config = ConfigParser()
config.read('config.ini')
# 应用分享配置参数

from flask import send_from_directory


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')



def get_client_ip():
    # 获取 X-Real-IP 请求头中的 IP 地址
    #ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    return get_public_ip()

def get_public_ip():
    # 使用 "ipify" 的 API 查询公共 IP 地址
    response = requests.get('https://api.ipify.org?format=json')
    if response.status_code == 200:
        ip_address = response.json()['ip']
        return ip_address
    else:
        return None

# 登录页面

def get_user_status():
    if 'logged_in' in session and session['logged_in']:
        return True
    else:
        return False


def get_username():
    if 'username' in session:
        return session['username']
    else:
        return None


@app.context_processor
def inject_variables():
    return dict(
        userStatus=get_user_status(),
        username=get_username(),
    )


@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'logged_in'  in session:
        return redirect(url_for('home'))
    else:
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


domain = config.get('general', 'domain').strip("'")

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


def check_banned_ip(ip_address):
    with open("banIP.txt", "r") as file:
        banned_ips = file.read().splitlines()
        if ip_address in banned_ips:
            return True
    return False



import xml.etree.ElementTree as ET


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        keyword = request.form.get('keyword')  # 获取搜索关键字
        matched_content = []

        files = os.listdir('articles')
        markdown_files = [file for file in files if file.endswith('.md')]

        # 创建XML根元素
        root = ET.Element('root')

        for file in markdown_files:
            article_name = file[:-3]  # 移除文件扩展名 (.md)
            encoded_article_name = urllib.parse.quote(article_name)  # 对文件名进行编码处理
            article_url = domain + 'blog/' + encoded_article_name
            date = get_file_date(encoded_article_name)
            describe = get_article_content(article_name, 10)
            describe = clearHTMLFormat(describe)

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
        match_data = ET.tostring(tree.getroot(), encoding='utf-8', method='xml').decode()

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

        if matched_content:
            return render_template('search.html', results=matched_content)

    return render_template('search.html', results=None)


import geoip2.database

def analyze_ip_location(ip_address):
    # 加载GeoIP2数据库文件
    reader = geoip2.database.Reader('static/GeoLite2-City.mmdb')


    try:
        # 查询IP地址的地理位置
        response = reader.city(ip_address)

        # 提取相关信息
        country = response.country.name
        city = response.city.name

        # 返回国家和城市信息
        return country, city

    except geoip2.errors.AddressNotFoundError:
        print("未找到该IP地址的地理位置信息")
        return None

    finally:
        # 关闭数据库连接
        reader.close()


import json
def update_visit(ip):
    # 读取visit_ip.txt中的记录
    with open('visit_ip.txt', 'r') as file:
        lines = file.readlines()

    # 检查是否存在该字段的记录
    field_exists = False
    for i, line in enumerate(lines):
        if line.startswith(f'{ip} '):
            field_exists = True
            # 将字段的值加1
            value = int(line.split()[1]) + 1
            # 更新行的内容
            lines[i] = f'{ip} {value}\n'

    # 如果不存在该字段的记录，则创建新的行
    if not field_exists:
        lines.append(f'{ip} 1\n')

    # 将更新后的记录写回visit_ip.txt文件
    with open('visit_ip.txt', 'w') as file:
        file.writelines(lines)

@app.route('/weather/<city_code>', methods=['GET'])
def get_weather(city_code):
    apiUrl = f'http://t.weather.itboy.net/api/weather/city/{city_code}'
    try:
        response = requests.get(apiUrl)
        weatherData = response.json()

        todayWeather = weatherData['data']['forecast'][0]
        tomorrowWeather = weatherData['data']['forecast'][1]
        dayAfterTomorrowWeather = weatherData['data']['forecast'][2]

        processedData = {
            'today': {
                'type': todayWeather['type'],
                'icon': get_weather_icon_url(todayWeather['type'])
            },
            'tomorrow': {
                'type': tomorrowWeather['type'],
                'icon': get_weather_icon_url(tomorrowWeather['type'])
            },
            'dayAfterTomorrow': {
                'type': dayAfterTomorrowWeather['type'],
                'icon': get_weather_icon_url(dayAfterTomorrowWeather['type'])
            }
        }

        return jsonify(processedData)
    except Exception as e:
        error_message = {'error': str(e)}
        return jsonify(error_message), 500

@app.route('/get_city_code', methods=['POST'])
def get_city_code():
    city_name = request.form.get('city_name')
    city_name = clearHTMLFormat(city_name)

    with open('static/cityCode.json', 'r', encoding='utf-8') as file:
        city_data = json.load(file)

    for city in city_data:
        if city['city_name'] == city_name:
            return jsonify({'city_code': city['city_code']})

    return jsonify({'error': '城市不存在'})

def get_weather_icon_url(weather_type):
    iconFileName = ""  # 默认图标文件名，根据实际情况修改

    if weather_type == "晴":
        iconFileName = "晴.png"
    elif weather_type == "阴":
        iconFileName = "阴.png"
    elif weather_type == "多云":
        iconFileName = "多云.png"
    elif weather_type == "小雨":
        iconFileName = "小雨.png"
    elif weather_type == "中雨":
        iconFileName = "中雨.png"
    elif weather_type == "大雨":
        iconFileName = "大雨.png"
    elif weather_type == "暴雨":
        iconFileName = "暴雨.png"
    elif weather_type == "大暴雨":
        iconFileName = "大暴雨.png"
    elif weather_type == "特大暴雨":
        iconFileName = "特大暴雨.png"
    elif weather_type == "阵雨":
        iconFileName = "阵雨.png"
    elif weather_type == "雷阵雨":
        iconFileName = "雷阵雨.png"
    elif weather_type == "雷阵雨伴有冰雹":
        iconFileName = "雷阵雨伴有冰雹.png"
    elif weather_type == "雨夹雪":
        iconFileName = "雨夹雪.png"
    elif weather_type == "阵雪":
        iconFileName = "阵雪.png"
    elif weather_type == "小雪":
        iconFileName = "小雪.png"
    elif weather_type == "中雪":
        iconFileName = "中雪.png"
    elif weather_type == "大雪":
        iconFileName = "大雪.png"
    elif weather_type == "暴雪":
        iconFileName = "暴雪.png"
    elif weather_type == "浮沉":
        iconFileName = "浮沉.png"
    elif weather_type == "雾":
        iconFileName = "雾.png"
    elif weather_type == "霾":
        iconFileName = "霾.png"
    elif weather_type == "冻雨":
        iconFileName = "冻雨.png"
    elif weather_type == "沙尘暴":
        iconFileName = "沙尘暴.png"
    elif weather_type == "扬沙":
        iconFileName = "扬沙.png"
    elif weather_type == "强沙尘暴":
        iconFileName = "强沙尘暴.png"
    else:
        iconFileName = "undefined.png"

    iconUrl = f'static/image/weather/{iconFileName}'
    return iconUrl


def convert_to_chinese(data):
    converted_data = []
    for item in data:
        response = requests.get(
            f'http://fanyi.youdao.com/translate?doctype=json&type=AUTO&i={item}'
        )
        if response.status_code == 200:
            try:
                translation = response.json()['translateResult'][0][0]['tgt']
                converted_data.append(translation)
            except Exception:
                converted_data.append(item)
        else:
            converted_data.append(item)
    return tuple(converted_data)

# 主页
import hashlib
def profile(email):
    email = email  # 用户的电子邮件地址
    # 将电子邮件地址转换为小写，并使用 MD5 哈希算法生成哈希值
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    # 构建 Gravatar 头像的 URL
    avatar_url = f'https://www.gravatar.com/avatar/{email_hash}?s=100&r=g&d=retro'

    return avatar_url



@app.route('/', methods=['GET', 'POST'])
def home():
    IPinfo = get_client_ip()
    update_visit(IPinfo)
    IPinfo= analyze_ip_location(IPinfo)
    IPinfo=convert_to_chinese(IPinfo)
    city_code = 101010100
    avatar_url=profile('guest@7trees.cn')
    if check_banned_ip(IPinfo):
        return render_template('error.html')
    else:
        if request.method == 'GET':
            page = request.args.get('page', default=1, type=int)  # 获取 URL 参数中的页码，默认为第一页
            articles, has_next_page, has_previous_page = get_article_names(page=page)  # 获取分页后的文章列表和翻页信息

            template = env.get_template('home.html')
            session.setdefault('theme', 'day-theme')
            notice = read_file('notice/1.txt', 50)
            userStatus = get_user_status()
            username = get_username()
            if userStatus and username != None:
                avatar_url=get_email(username)
                avatar_url=profile(avatar_url)
            return template.render(articles=articles, url_for=url_for, theme=session['theme'],
                               notice=notice,avatar_url=avatar_url,
                               has_next_page=has_next_page, has_previous_page=has_previous_page, current_page=page, userStatus=userStatus,username=username,IPinfo=IPinfo,city_code=city_code)
        else:
            return render_template('home.html')


@app.route('/blog/<article>', methods=['GET', 'POST'])
def blog_detail(article):
    try:
        # 根据文章名称获取相应的内容并处理
        article_name = article
        article_Surl= domain+'blog/'+article_name
        article_url = "https://api.7trees.cn/qrcode/?data="+article_Surl
        author = get_blog_author()
        blogDate = get_file_date(article_name)

        if 'theme' not in session:  # 检查session中是否存在theme键
            session['theme'] = 'day-theme'  # 如果不存在，则设置默认主题为白天（day-theme）

        article_content = get_article_content(article, 215)
        article_summary=clearHTMLFormat(article_content)
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
                               url_for=url_for,username=username,article_url=article_url,article_Surl=article_Surl,article_summary=article_summary)
    except FileNotFoundError:
        return redirect(url_for('undefined_route'))


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


@app.route('/post_comment', methods=['POST'])
def post_comment():
    article_name = request.form.get('article_name')
    username = request.form.get('username')
    comment = request.form.get('comment')
    return zy_post_comment(article_name, username,comment)






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

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    return zy_upload_file()


@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    return zy_delete_file(filename)





@app.route('/<path:undefined_path>')
def undefined_route(undefined_path):
    return render_template('404.html'), 404



