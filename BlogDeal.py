import configparser
import random
import urllib
import markdown
from configparser import ConfigParser
from database import get_database_connection
from dingtalkchatbot.chatbot import DingtalkChatbot
import os
from urllib.parse import quote_plus
from user import error
import datetime

def get_article_names(page=1, per_page=10):
    articles = []
    files = os.listdir('articles')
    markdown_files = [file for file in files if file.endswith('.md')]

    # Sort markdown_files in reverse order based on modified date
    markdown_files = sorted(markdown_files, key=lambda f: datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join('articles', f))), reverse=True)

    start_index = (page-1) * per_page
    end_index = start_index + per_page

    for file in markdown_files[start_index:end_index]:
        article_name = file[:-3]  # Remove the file extension (.md)
        articles.append(article_name)

    # Check if each article is in hidden.txt and remove it if necessary
    hidden_articles = read_hidden_articles()
    articles = [article for article in articles if article not in hidden_articles]

    has_next_page = end_index < len(markdown_files)
    has_previous_page = start_index > 0

    return articles, has_next_page, has_previous_page

def read_hidden_articles():
    with open('articles/hidden.txt', 'r', encoding='utf-8') as hidden_file:
        hidden_articles = hidden_file.read().splitlines()
    return hidden_articles

import codecs
import misaka
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

class HighlightRenderer(misaka.HtmlRenderer):
    def blockcode(self, text, lang):
        if lang:
            lexer = get_lexer_by_name(lang, stripall=True)
        else:
            lexer = get_lexer_by_name('text')
        formatter = HtmlFormatter()
        highlighted_code = highlight(text.rstrip(), lexer, formatter)
        return f'<div class="highlight"><pre>{highlighted_code}</pre></div>'




def get_article_content(article, limit):
    try:
        with codecs.open(f'articles/{article}.md', 'r', encoding='utf-8') as f:
            content = f.read()

        renderer = HighlightRenderer()
        md = misaka.Markdown(renderer, extensions=misaka.EXT_FENCED_CODE)
        lines = content.split('\n')
        lines_limit = min(limit, len(lines))
        line_counter = 0
        html_content = ''
        readNav = []
        in_code_block = False
        code_block_content = ''

        for line in lines:
            if line_counter >= lines_limit:
                break

            if line.startswith('```'):
                if in_code_block:
                    html_content += f'<div class="highlight"><pre><code class="language-{code_lang}">{code_block_content.strip()}</code></pre></div>'
                    in_code_block = False
                    code_block_content = ''
                else:
                    in_code_block = True
                    code_lang = line.split('```')[1].strip()
            elif in_code_block:
                code_block_content += line + '\n'
            else:
                if line.startswith('#'):
                    header_level = len(line.split()[0]) + 2
                    header_title = line.strip('#').strip()
                    anchor = header_title.lower().replace(" ", "-")
                    readNav.append(
                        f'<a href="#{anchor}">{md("#" * header_level + " " + header_title)}</a>'
                    )
                    line = f'<h{header_level} id="{anchor}">{header_title}</h{header_level}>'

                html_content += md(line)

            line_counter += 1

        if in_code_block:
            html_content += '</code></pre></div>'

        return html_content, '\n'.join(readNav)

    except FileNotFoundError:
        # 文件不存在时返回404错误页面
        return error('No file', 404)

import re


def clearHTMLFormat(text):
    clean_text = re.sub('<.*?>', '', str(text))
    return clean_text


def zy_get_comment(article_name, page=1, per_page=10):
    db = get_database_connection()
    cursor = db.cursor()
    try:
        query = "SELECT * FROM comments WHERE article_name = %s ORDER BY add_date DESC LIMIT 70 OFFSET %s"

        offset = (page - 1) * per_page
        cursor.execute(query, (article_name, offset))
        #print("Total rows fetched:", cursor.rowcount)

        results = []
        rows = cursor.fetchall()


        for row in rows:
            username = row[0]
            comment = row[2]
            result_dict = {'username': username, 'comment': comment}
            results.append(result_dict)

        return results
    except Exception as e:
        print("An error occurred:", str(e))
        return []
    finally:
        cursor.close()
        db.close()


def zy_post_comment(article_name, username, comment):
    # 检查用户名是否为None
    if username == 'None':
        return "未登录用户无法评论"

    db = get_database_connection()
    cursor = db.cursor()

    # SQL语句将评论插入到 'comments' 表中
    sql = "INSERT INTO comments (username, article_name, comment) VALUES (%s, %s, %s)"

    # 要插入到表中的数据
    values = (username, article_name, comment)

    try:
        # 使用提供的数据执行SQL语句
        cursor.execute(sql, values)

        # 提交事务以保存更改
        db.commit()

        # 打印成功消息
        message = '您的文章' + article_name + '有了新的评论'
        return "评论成功"


    except Exception as e:
        # 如果发生错误，回滚事务
        db.rollback()

        # 打印错误消息
        return "评论失败"

    finally:
        # 关闭游标和数据库连接
        cursor.close()
        db.close()


def generate_random_text():
    # 生成随机的验证码文本
    characters = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    captcha_text = ''.join(random.choices(characters, k=4))
    return captcha_text


def get_blog_author(article_name):
    # 创建ConfigParser对象
    config = configparser.ConfigParser()

    # 读取配置文件
    config.read('author/mapper.ini', encoding='utf-8')

    # 获取article_name对应的作者
    articleAuthor = config.get('author', article_name, fallback=config.get('default', 'default'))

    # 移除单引号
    articleAuthor = articleAuthor.replace("'", "")

    return articleAuthor


def get_file_date(file_path):
    try:
        decoded_name = urllib.parse.unquote(file_path)  # 对文件名进行解码处理
        file_path = os.path.join('articles', decoded_name + '.md')
        # 获取文件的创建时间
        create_time = os.path.getctime(file_path)
        # 获取文件的修改时间
        modify_time = os.path.getmtime(file_path)
        # 获取文件的访问时间
        access_time = os.path.getatime(file_path)

        formatted_modify_time = datetime.datetime.fromtimestamp(modify_time).strftime("%Y-%m-%d %H:%M:%S")

        return formatted_modify_time

    except FileNotFoundError:
        # 处理文件不存在的情况
        return None


def zySendMessage(message):
    config = ConfigParser()
    config.read('config.ini', encoding='utf-8')
    access_token = config.get('messageBot', 'access_token').strip("'")
    webhook_url = 'https://oapi.dingtalk.com/robot/send?access_token=' + access_token
    dingbot = DingtalkChatbot(webhook_url)
    #red_msg = '<font color="#dd0000">级别:危险</font>'
    orange_msg = '<font color="#FFA500">级别:警告</font>'

    now_time = datetime.now().strftime('%Y.%m.%d %H:%M:%S')
    url = 'https://237127.xyz/'
    dingbot.send_markdown(
        title=f'新消息',
        text=f'### **我是主内容的第一行**\n'
             #f'**{red_msg}**\n\n'
             f'**{orange_msg}**\n\n'
             f'**{message}**\n\n'
             f'**发送时间:**  {now_time}\n\n'
             f'**相关网址:**[点击跳转]({url}) \n',
        is_at_all=True)


def authArticles(articleName, username):
    article_map = {}
    with open('author/mapper.ini', 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line in lines:
        line = line.strip()
        if line and '=' in line:
            article_info = line.split('=')
            if len(article_info) == 2:
                article_name = article_info[0].strip()
                article_owner = article_info[1].strip().strip('\'')
                article_map[article_name] = article_owner

    # Check if articleName exists in the article_map and owner matches the username
    if articleName in article_map and article_map[articleName] == username:
        #print("edit Author check")
        return True

    return False




def zyShowArticle(content):
    try:
        markdown_text = content
        html = markdown.markdown(markdown_text)
        return html
    except:
        # 发生任何异常时返回一个错误页面，可以根据需要自定义错误消息
        return error('Error in displaying the article')

def zyFEditArticle(article):
    limit = 215  # 读取的最大行数
    try:
        with codecs.open(f'articles/{article}.md', 'r', encoding='utf-8-sig', errors='replace') as f:
            lines = []
            for line in f:
                try:
                    lines.append(line)
                except UnicodeDecodeError:
                    # 在遇到解码错误时跳过当前行
                    pass

                if len(lines) >= limit:
                    break

        return ''.join(lines)
    except FileNotFoundError:
        # 文件不存在时返回 404 错误页面
        return error('No file', 404)



