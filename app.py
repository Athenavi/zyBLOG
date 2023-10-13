import datetime
import logging
import random
import time
import urllib
import json
import os
import portalocker
import requests
import xml.etree.ElementTree as ET
import geoip2.database
from configparser import ConfigParser
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, redirect, session, request, url_for, Response,jsonify,send_from_directory,send_file
from jinja2 import Environment, select_autoescape, FileSystemLoader
from werkzeug.middleware.proxy_fix import ProxyFix
from AboutLogin import zylogin, zyregister, get_email, profile
from AboutPW import zychange_password, zyconfirm_password
from BlogDeal import get_article_names, get_article_content, clearHTMLFormat, zy_get_comment, zy_post_comment, \
    get_file_date, get_blog_author, generate_random_text, read_hidden_articles
from templates.custom import custom_max, custom_min
from database import get_database_connection
from user import zyadmin, zy_delete_file
from utils import zy_upload_file, get_user_status, get_username, get_client_ip, read_file, \
    check_banned_ip, get_weather_icon_url
from flask_caching import Cache

template_dir = 'templates'  # 模板文件的目录
loader = FileSystemLoader(template_dir)
env = Environment(loader=loader, autoescape=select_autoescape(['html', 'xml']))
env.filters['custom_max'] = custom_max
env.filters['custom_min'] = custom_min
env.add_extension('jinja2.ext.loopcontrols')

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)
app.jinja_env = env
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = datetime.timedelta(hours=3)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)  # 添加 ProxyFix 中间件

logging.basicConfig(filename='app.log', level=logging.DEBUG)

config = ConfigParser()
config.read('config.ini')
# 应用分享配置参数
from datetime import datetime, timedelta
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')






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
    cache_dir = 'temp'
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = os.path.join(cache_dir, f'{city_code}.json')

    # Check if cache file exists and is within one hour
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            cache_timestamp = datetime.fromisoformat(cache_data.get('timestamp'))
            if datetime.now() - cache_timestamp <= timedelta(hours=1):
                return jsonify(cache_data)

    # Acquire a lock before generating cache file
    lock_file = f'{cache_file}.lock'
    try:
        with portalocker.Lock(lock_file, timeout=1) as lock:
            # Check again if cache file is created by another request
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    cache_timestamp = datetime.fromisoformat(cache_data.get('timestamp'))
                    if datetime.now() - cache_timestamp <= timedelta(hours=1):
                        return jsonify(cache_data)

            apiUrl = f'http://t.weather.itboy.net/api/weather/city/{city_code}'
            try:
                response = requests.get(apiUrl)
                weatherData = response.json()

                todayWeather = weatherData['data']['forecast'][0]
                tomorrowWeather = weatherData['data']['forecast'][1]
                dayAfterTomorrowWeather = weatherData['data']['forecast'][2]

                processedData = {
                    'timestamp': datetime.now().isoformat(),
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
    city_name = clearHTMLFormat(city_name)
    return zy_get_city_code(city_name)



@app.route('/profile', methods=['GET', 'POST'])
def space():
    city_code = 101010100
    avatar_url=profile('guest@7trees.cn')
    template = env.get_template('profile.html')
    session.setdefault('theme', 'day-theme')
    notice = read_file('notice/1.txt', 50)
    userStatus = get_user_status()
    username = get_username()
    if userStatus and username != None:
        avatar_url=get_email(username)
        avatar_url=profile(avatar_url)
    return template.render(url_for=url_for, theme=session['theme'],
                               notice=notice,avatar_url=avatar_url,userStatus=userStatus,username=username,city_code=city_code)


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




# 主页
@app.route('/', methods=['GET', 'POST'])
def home():
    IPinfo = get_client_ip()
    update_visit(IPinfo)
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
    IPinfo = get_client_ip()
    update_visit(IPinfo)
    if check_banned_ip(IPinfo):
        return render_template('error.html')
    else:
        try:
            # 根据文章名称获取相应的内容并处理
            article_name = article
            article_names = get_article_names()
            if article_name not in article_names[0]:
                return render_template('404.html'), 404

            hidden_articles = read_hidden_articles()

            if article_name in hidden_articles:
                return render_template('404.html'), 404

            article_Surl = domain + 'blog/' + article_name
            article_url = "https://api.7trees.cn/qrcode/?data=" + article_Surl
            author = get_blog_author(article_name)
            blogDate = get_file_date(article_name)

            # 检查session中是否存在theme键
            if 'theme' not in session:
                session['theme'] = 'day-theme'  # 如果不存在，则设置默认主题为白天（day-theme）

            article_content = get_article_content(article, 215)
            article_summary = clearHTMLFormat(article_content)
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
                                    article_Surl=article_Surl, article_summary=article_summary)

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
            with open(cache_file, 'r') as f:
                cached_xml_data = f.read()
            response = Response(cached_xml_data, mimetype='application/rss+xml')
            return response

    files = os.listdir('articles')
    markdown_files = [file for file in files if file.endswith('.md')]

    # 创建XML文件头及其他信息...
    xml_data = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_data += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml_data += '<channel>\n'
    xml_data += '<title>Your RSS Feed Title</title>\n'
    xml_data += '<link>'+domain+'</link>\n'
    xml_data += '<description>Your RSS Feed Description</description>\n'
    xml_data += '<language>en-us</language>\n'
    xml_data += '<lastBuildDate>' + datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") + '</lastBuildDate>\n'
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

    # 写入缓存文件
    with open(cache_file, 'w') as f:
        f.write(xml_data)

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



@app.route('/generate_captcha')
def generate_captcha():
    # 生成验证码文本
    captcha_text = generate_random_text()

    # 创建一个新的图像对象
    image = Image.new('RGB', (135, 80), color = (255, 255, 255))

    # 创建字体对象并设置字体大小
    font = ImageFont.truetype('arial.ttf', size=40)

    # 在图像上绘制验证码文本
    d = ImageDraw.Draw(image)
    d.text((35, 20), captcha_text, font=font, fill=(0, 0, 0))

    # 保存图像到临时文件
    image.save('captcha.png')
    convert_white_to_transparent('captcha.png')
    # 将验证码文本存储在session中，用于校对
    session['captcha_text'] = captcha_text

    # 返回生成的验证码图像给用户
    return send_file('captcha.png', mimetype='image/png')

def convert_white_to_transparent(image_path):
    # 打开图像
    image = Image.open(image_path)
    image = image.convert("RGBA")

    # 获取图像的像素数据
    data = image.getdata()

    # 创建一个新的像素数据列表，将白色的像素转换为透明，其他像素保持不变
    new_data = []
    for item in data:
        # 如果像素是白色
        if item[:3] == (255, 255, 255):
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    # 将新的像素数据设置回图像
    image.putdata(new_data)

    # 保存图像
    image.save("captcha.png", "PNG")








@app.route('/verify_captcha', methods=['POST'])
def verify_captcha():
    # 获取前端传来的验证码值
    user_input = request.form.get('captcha')
    user_input = clearHTMLFormat(user_input)

    # 获取存储在session中的验证码文本
    captcha_text = session['captcha_text']

    if user_input.lower() == captcha_text.lower():
        # 验证码匹配成功，执行相应逻辑
        return '验证码匹配成功'
    else:
        # 验证码匹配失败，执行相应逻辑
        return '验证码不匹配'

