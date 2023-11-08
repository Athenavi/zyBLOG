# zyBLOG - 一个简易的博客程序


## 简介

[zyBLOG](https://github.com/Athenavi/zyBLOG) 是一个基于 Python Flask 和 WSGI 的简易博客程序

（以下demo网址非最新特性）
demo https://237127.xyz
## 功能特点

<details>
<summary>TODO List</summary>

- [ ] 界面适应手机 
- [ ] 提供文章分类和标签功能，方便用户组织和浏览文章。
- [ ] 支持创建、编辑和删除博客文章。
- [x] 提供评论功能，让用户可以与其他用户进行交流和互动。
- [x] 用户可以注册和登录，以便管理他们的博客文章。
- [x] 博客文章可以包含图片、视频和代码片段。
- [x] 支持搜索功能，使用户可以快速找到感兴趣的文章。 

</details>

## 技术组成

zyBLOG 使用以下技术组成：

- **Python Flask**: 作为 Web 框架，提供了构建网页应用的基础功能。
- **WSGI**: 作为 Python Web 应用程序与 Web 服务器之间的接口标准，实现了 Web 应用程序与服务器之间的通信。
- **HTML/CSS**: 用于构建博客界面的前端技术。
- **MySQL**: 作为数据库，用于存储用户、文章评论等数据。

## 如何运行
windows 系统可直接使用 ~zyBlog_V1.0.0.exe~ 
1. 确保你的系统已经安装了 Python 和 pip。
2. 克隆或下载 zyBLOG 代码库到本地。创建一个数据库，导入本项目里的sql，配置config.ini
3. 在终端中进入项目目录，并执行以下命令以启动 zyBLOG：

```bash
$ python wsgi.py
```
5. 根据app.log的提示安装所需要的库，或者自行查阅requirements.txt（txt文档可能会过时）。
6. 在浏览器中访问 `http://localhost:5000`，即可进入 zyBLOG。
7. 默认管理员账号 'test' 默认密码 '123456'
## 鸣谢

 https://7trees.cn 提供API支持
 API可参阅 https://qks.icu/apiFox

## 免责声明

zyBLOG 是一个个人项目，并未经过详尽测试和完善，因此不对其能力和稳定性做出任何保证。使用 zyBLOG 时请注意自己的数据安全和程序稳定性。任何由于使用 zyBLOG 造成的数据丢失、损坏或其他问题，作者概不负责。

**请谨慎使用 zyBLOG，并在使用之前备份你的数据。**
