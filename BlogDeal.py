import os
import codecs
import markdown
import datetime
import os


from database import get_database_connection

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

    has_next_page = end_index < len(markdown_files)
    has_previous_page = start_index > 0

    return articles, has_next_page, has_previous_page



def get_article_content(article, limit):
    lines_limit = limit
    with codecs.open(f'articles/{article}.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    article_content = ''.join(lines[:lines_limit])
    html_content = markdown.markdown(article_content)
    return html_content

import re

def clearHTMLFormat(text):
    # 使用正则表达式清除HTML标记
    clean_text = re.sub('<.*?>', '', text)
    return clean_text




def zy_get_comment(article_name, page=1, per_page=10):
    db = get_database_connection()
    cursor = db.cursor()
    try:
        query = "SELECT * FROM comments WHERE article_name = %s ORDER BY add_date DESC LIMIT 70 OFFSET %s"

        offset = (page - 1) * per_page
        cursor.execute(query, (article_name, offset))
        print("Total rows fetched:", cursor.rowcount)

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
