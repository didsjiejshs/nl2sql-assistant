# 如何把这个 Demo 放到 GitHub 上

> 目标：让别人打开你的 GitHub 仓库，看到代码、看到说明、并且**能自己跑起来**。

---

## 第 0 步：先确认项目能跑

在项目目录下依次执行：

```bash
pip install -r requirements.txt
python -m data.seed      # 生成数据库
python main.py           # 启动服务
```

浏览器打开 http://127.0.0.1:8000 看到页面 = 成功。

---

## 第 1 步：注册 GitHub 账号

1. 打开 https://github.com/signup
2. 用户名建议用**拼音 + 数字**，例如 `zhujiang-dev`、`zhujiang2027`——
   **别用中文或乱码**，因为将来面试官要念出来、要输网址。
3. 邮箱用你简历上的那个 `3365264404@qq.com`，这样 HR 能对上人。

---

## 第 2 步：安装 Git

下载：https://git-scm.com/download/win

安装时一路默认即可。装完打开 PowerShell 验证：

```bash
git --version
```

---

## 第 3 步：配置 Git 身份（只需一次）

```bash
git config --global user.name "朱江"
git config --global user.email "3365264404@qq.com"
```

---

## 第 4 步：在本地初始化仓库

**先确认 `.gitignore` 已经生效**（这个文件我已经写好了），它会把 `.venv/`、`.env`、`__pycache__` 排除掉，
**尤其是 `.env`（含 API Key）绝对不能被提交**。

```bash
cd 你的项目目录

git init
git add .
git status          # 检查一下，确认没有 .env 和 .venv
git commit -m "feat: 产线数据问答助手 - NL2SQL 应用首次提交"
```

---

## 第 5 步：在 GitHub 网站创建仓库

1. 登录 GitHub，点右上角 **+** → **New repository**
2. **Repository name** 填 `nl2sql-assistant`
3. **Description** 填：
   > 用中文提问，自动生成 SQL 并可视化 —— 基于 FastAPI + 大模型的 NL2SQL 数据问答应用
4. 选择 **Public**（公开，面试官才看得到）
5. ⚠️ **不要勾选** Add a README file / .gitignore / license（本地已经有了，勾了会冲突）
6. 点 **Create repository**

---

## 第 6 步：把本地代码推上去

创建完成后 GitHub 会显示一段命令，用下面这三行（把 `你的用户名` 换成你的）：

```bash
git remote add origin https://github.com/你的用户名/nl2sql-assistant.git
git branch -M main
git push -u origin main
```

> 第一次推送会弹出登录窗口，选择 **Sign in with your browser**，在浏览器里授权即可。

推送成功后刷新仓库页面，就能看到代码了。

---

## 第 7 步：给仓库「装修」一下（重要）

面试官点进来只有 10 秒耐心，做好这 3 件事：

### ① 加截图

1. 本地启动服务，浏览器打开 http://127.0.0.1:8000
2. 输入「哪条产线的不良率最高？」，等图表出来
3. 用 `Win + Shift + S` 截图，保存为 `docs/screenshot.png`
4. 在 README 的标题下面插入一行：

```markdown
![界面截图](docs/screenshot.png)
```

**一张界面截图，比 1000 字说明都管用。**

### ② 加仓库 Topics（标签）

在仓库首页右侧点齿轮，添加：

```
nl2sql  llm  fastapi  python  data-analysis  text-to-sql  echarts
```

这些标签会让你的仓库出现在 GitHub 搜索里。

### ③ 在 GitHub 个人主页「钉住」这个仓库

进入你自己的主页 → **Customize your pins** → 勾选 `nl2sql-assistant`。
这样面试官点开你的 GitHub 主页，第一眼看到的就是它。

---

## 第 8 步：把这个链接写进简历

在简历头部的联系方式那一行加上：

```
朱江 ｜ 男 ｜ 22 岁 ｜ 13034744783 ｜ 3365264404@qq.com
GitHub：github.com/你的用户名/nl2sql-assistant
```

**投开发岗没有代码链接是硬伤**——这一步做完，你的简历就比同届大多数人扎实了。

---

## 常见问题

**Q：推送时提示 `failed to push some refs`？**
A：多半是创建仓库时勾了 README。执行 `git pull --rebase origin main` 后再 push。

**Q：不小心把 `.env` 提交上去了？**
A：立刻去对应平台**吊销那个 API Key**，然后 `git rm --cached .env` 重新提交。
   **Key 一旦推到公开仓库，几分钟内就会被爬虫扫走盗刷，必须吊销，不能只删文件。**

**Q：以后改了代码怎么更新？**
A：三行命令：
```bash
git add .
git commit -m "描述你改了什么"
git push
```

**Q：想让它有个在线可访问的网址？**
A：两种免费方案：

| 方案 | 说明 |
|---|---|
| **Hugging Face Spaces** | 支持 FastAPI 应用，免费，会给你一个 `xxx.hf.space` 的公网地址 |
| **Render / Railway** | 支持 Docker 部署，免费额度够 Demo 用 |

> 建议先把 GitHub 做好。有公网地址是加分项，不是必需项。

---

## 一句话总结流程

```
装 Git → git config → git init → git add/commit
   → GitHub 建仓库（不勾 README）→ git remote add → git push
   → 加截图 + Topics + Pin → 链接写进简历
```

全程大约 30 分钟。