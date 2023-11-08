
    function loadPage(url, containerId) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', url, true);

      xhr.onload = function () {
        if (xhr.status === 200) {
          var tempDiv = document.createElement('div');
          tempDiv.innerHTML = xhr.responseText;

          var newCommentsContainer = tempDiv.querySelector('#' + containerId);
          var currentCommentsContainer = document.getElementById(containerId);

          if (newCommentsContainer && currentCommentsContainer) {
            currentCommentsContainer.innerHTML = newCommentsContainer.innerHTML;
          }
        }
      };

      xhr.send();
    }
    function postComment(event) {
    event.preventDefault();  // 防止默认的表单提交行为

    var articleName = document.getElementById('article_name').value;
    var username = document.getElementById('username').value;
    var comment = document.getElementById('comment').value;
    var captcha = document.getElementById('captcha').value;

    // 发送请求以验证验证码
    fetch('/verify_captcha', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: 'captcha=' + captcha
    })
      .then(function(response) {
        return response.text();
      })
      .then(function(result) {
        // 如果验证码匹配成功，执行评论逻辑
        if (result === '验证码匹配成功') {
          var xhr = new XMLHttpRequest();
          xhr.open('POST', '/post_comment', true);
          xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
          xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 200) {
              var response = JSON.parse(xhr.responseText);
              document.getElementById('result').innerText = response.result;

              // 如果评论成功，清空评论输入框
              if (response.result === '评论成功') {
                document.getElementById('comment').value = '';

                // 用新添加的评论更新现有评论部分
                // 用新添加的评论更新现有评论部分
                var commentsSection = document.getElementById('comments-container');
                var newComment = document.createElement('li');
                newComment.className = 'list-group-item';  // 应用相同的样式类
                var commentUsername = document.createElement('span');
                commentUsername.className = 'fw-bold';  // 应用相同的样式类
                commentUsername.innerText = response.username + ": ";
                newComment.appendChild(commentUsername);
                var commentText = document.createTextNode(response.comment);
                newComment.appendChild(commentText);
                commentsSection.querySelector('ul').appendChild(newComment);

                // 刷新验证码图像
                generateCaptcha();
              }
            }
          };
          xhr.send('article_name=' + articleName + '&username=' + username + '&comment=' + comment);
        } else {
          // 验证码不匹配，提示用户
          alert('验证码不匹配');
          // 刷新验证码图像
          generateCaptcha();
        }
      })
      .catch(function(error) {
        console.error(error);
      })
      .finally(function() {
        // 重新注册点击事件，以刷新验证码图像
        var captchaImage = document.getElementById('captcha-image');
        captchaImage.addEventListener('click', generateCaptcha);
      });
  }
  function generateCaptcha() {
  var captchaImage = document.getElementById('captcha-image');
  fetch('/generate_captcha')
    .then(function (response) {
      return response.json(); // Parse the response as JSON
    })
    .then(function (result) {
      // Update the captcha image source with the base64 image data
      captchaImage.src = 'data:image/jpeg;base64,' + result.image;
      captchaImage.alt = result.captcha_text;
    })
    .catch(function (error) {
      console.error(error);
      // Handle any errors if necessary
    });
}

  // 在表单提交时调用评论函数
  var form = document.getElementById('comment_form');
  form.addEventListener('submit', postComment);

  // 生成初始验证码图像
  generateCaptcha();

  // 检测设备类型
  var isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  // 根据设备类型添加样式
  if (isMobile) {
    document.addEventListener("DOMContentLoaded", function() {
      var showOnDesktopDiv = document.querySelector(".show-on-desktop");
      if (showOnDesktopDiv) {
        showOnDesktopDiv.style.display = "none";
      }
    });
  }

    function toggleSidebar() {
  var sidebar = document.getElementById("sidebar");
  if (sidebar.style.display === "none") {
    sidebar.style.display = "block";
  } else {
    sidebar.style.display = "none";
  }
}
var pageContent = document.body.innerText;
// 检测是否包含作者单词
if (pageContent.includes("author")) {
  // 创建一个新的button元素
  var button = document.createElement("button");
  button.setAttribute("onclick", "toggleSidebar()");
  button.innerText = "显示/隐藏侧边栏";

  // 将按钮添加到<div id="SideList"></div>之间
  var sideList = document.getElementById("SideList");
  sideList.insertBefore(button, sideList.firstChild);
}

    if (window !== window.top) {
  // 当前窗口被嵌套在另一个iframe中
  alert('当前视图会影响您的体验！！！\n请点击搜索结果后的小图标进行访问');
  window.location.href = '/search';
}


// 使用 JavaScript 代码实现
var sidebar = document.getElementById('sidebar');
var initialX = null;

sidebar.addEventListener('mousedown', function(event) {
  event.preventDefault();
  initialX = event.clientX;
  document.addEventListener('mousemove', moveElement);

  document.addEventListener('mouseup', function() {
    document.removeEventListener('mousemove', moveElement);
    initialX = null;
  });

  function moveElement(event) {
    var deltaX = event.clientX - initialX;
    var newX = sidebar.offsetLeft + deltaX;
    sidebar.style.left = newX + 'px';
    initialX = event.clientX;
  }
});

// 使用 jQuery 实现
$('#sidebar').draggable({
  axis: 'x'  // 限制只能在水平方向拖动
});