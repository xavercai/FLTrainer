# 德语跟读课堂 · 在线版（GitHub Pages）

手机上独立运行、每天自动更新素材的版本。不需要电脑，不需要本地 Python。

## 这套东西怎么运作

| 文件 | 作用 |
| --- | --- |
| `index.html` | 工具本体（单文件，就是原来的 `deutsch-news-coach.html`） |
| `news/daily.json` | 当天素材，页面打开时读它（同源，无跨域问题） |
| `scripts/fetch_daily.py` | 抓德语新闻、挑 3–5 句、写 `news/daily.json`（纯标准库） |
| `.github/workflows/daily.yml` | 每天北京时间 05:00 自动跑上面的脚本并提交 |

页面加载顺序：先读 `news/daily.json` → 没有/过期就退回浏览器自己抓 RSS → 再不行用内置 105 句 A1 语料。任何一步失败都不会白屏。

## 一次性部署（约 10 分钟）

1. **建仓库**：打开 github.com → 右上 `+` → `New repository` → 名字随意（如 `deutsch-coach`）→ 选 **Public** → `Create repository`。
   > 免费账号的 Pages 只支持公开仓库。本包不含任何密钥或个人信息，公开没问题。想用私有仓库需要 GitHub Pro。

2. **上传文件**：仓库页 → `Add file` → `Upload files` → 把本文件夹里的**全部内容**拖进去（`index.html`、`.nojekyll`、以及 `news/`、`scripts/`、`.github/` 三个文件夹）→ `Commit changes`。
   > `.github` 是隐藏文件夹；Windows 资源管理器里需要先勾选「查看 → 显示 → 隐藏的项目」才能看到它。用网页上传时直接拖文件夹即可。

3. **打开 Pages**：仓库 `Settings` → 左侧 `Pages` → Source 选 `Deploy from a branch` → Branch 选 `main`、目录选 `/ (root)` → `Save`。

4. 等约 1 分钟，访问 `https://<你的GitHub用户名>.github.io/<仓库名>/`，页面能出来就成功了。

5. **手动跑一次素材抓取**：仓库 `Actions` 标签 → 左侧 `daily-news` → `Run workflow` → 绿色按钮。跑完 `news/daily.json` 会被更新成真实新闻。

## 在手机上配好

1. 用 **Safari** 打开第 4 步的网址。
2. 进「**⑥ 设置 → ☁️ 云 TTS**」：`provider` 选 **Azure**，填入 **Key** 和 **Region**，`voice` 选 `de-DE-ConradNeural`（就是 Conrad 男声），点测试，能出声就保存。
3. 回到「**① 今日课堂**」，确认顶部来源标签显示「**每日更新**」。
4. 点 Safari「**分享 → 添加到主屏幕**」，以后从桌面图标进，全屏无地址栏。

## 每天自动更新

- 每天 **05:00（北京时间）** GitHub 的服务器会抓一次德国新闻，生成 `news/daily.json` 并提交，Pages 自动重新部署。GitHub 服务器在境外，能直连德国新闻站，不受公司网络限制。
- 想改时间：编辑 `.github/workflows/daily.yml` 里的 `cron`（UTC 时间）。想增删新闻源：编辑 `scripts/fetch_daily.py` 顶部的 `FEEDS`。

## 注意

- **Key 只存在手机浏览器本地**（localStorage），不要用公司共享账号。
- Action 抓不到任何源时**不会覆盖**旧文件，站点上始终有素材。
- 本地双击 `index.html` 也能用，只是那种情况读不到 `news/daily.json`，会退回内置语料。
- Azure 免费层（F0）每月 50 万字符神经语音，个人练句子用不完。
