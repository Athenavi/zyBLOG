import os
import string
import random
import requests
import urllib
from flask import request, make_response, session
from user import error
from werkzeug.utils import secure_filename


def generate_short_url():
    characters = string.ascii_letters + string.digits
    short_url = ''.join(random.choice(characters) for _ in range(6))
    return short_url


ALLOWED_EXTENSIONS = {
    'txt': 5 * 1024 * 1024,  # 5MB
    'jpg': 10 * 1024 * 1024,  # 10MB
    'png': 10 * 1024 * 1024,  # 10MB
    'md': 5 * 1024 * 1024  # 10MB

}


def allowed_file(filename):
    # 检查文件扩展名是否在允许的列表中
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def zy_upload_file():
    if request.method == 'POST':
        # 检查是否有文件被上传
        if 'file' not in request.files:
            return error('No file uploaded', 400)

        file = request.files['file']

        # 检查用户是否选择了文件
        if file.filename == '':
            return error('No file selected', 400)

        # 检查文件类型和大小是否在允许范围内
        if not allowed_file(file.filename) or file.content_length > 10 * 1024 * 1024:
            return error('Invalid file', 400)

        type = request.form.get('type')

        # 根据类型选择保存目录
        if type == 'articles':
            save_directory = 'articles/'
        elif type == 'notice':
            save_directory = 'notice/'
        else:
            return error('Invalid type', 400)

        # 检查保存目录是否存在，不存在则创建它
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # 保存文件到服务器上的指定目录，覆盖同名文件
        file.save(os.path.join(save_directory, secure_filename(file.filename)))

        return 'File uploaded successfully'

    return make_response('success')


def get_client_ip():
    # 尝试从session中读取ip
    public_ip = session.get('public_ip')
    if public_ip:
        return public_ip

    # 获取 X-Real-IP 请求头中的 IP 地址
    real_ip = request.headers.get('X-Real-IP')

    if real_ip:
        return real_ip

    # 获取公共IP地址
    try:
        response = requests.get('http://ip-api.com/json')
        data = response.json()
        if data['status'] == 'success':
            public_ip = data['query']
        else:
            public_ip = ''
    except requests.RequestException:
        public_ip = ''

    # 将ip存入session中
    session['public_ip'] = public_ip

    return public_ip


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


# 获取系统默认编码
def zySaveEdit(articleName, content):
    if articleName and content:
        save_directory = 'articles/'

        # 将文章名转换为字节字符串
        article_name_bytes = articleName.encode('utf-8')

        # 将字节字符串和目录拼接为文件路径
        file_path = os.path.join(save_directory, article_name_bytes.decode('utf-8') + ".md")

        # 检查保存目录是否存在，如果不存在则创建它
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # 将文件保存到指定的目录上，覆盖任何已存在的文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

        return make_response('success')

    return make_response('failed: articleName or content is empty')