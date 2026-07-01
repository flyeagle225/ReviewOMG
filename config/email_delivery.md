# ReviewOMG 邮件推送配置

每日行业新闻和每周博客选题池会优先写入 Obsidian/GitHub，同时可以作为 Markdown 附件发送到飞书邮箱。

需要在 GitHub 仓库中配置以下 Secrets：

1. `FEISHU_EMAIL`
   - 你的飞书邮箱收件地址。
   - 例如：`name@example.com`

2. `SMTP_SERVER`
   - 发件邮箱的 SMTP 服务器。
   - 例如 Gmail：`smtp.gmail.com`
   - 例如 Outlook：`smtp.office365.com`
   - 例如 QQ 邮箱：`smtp.qq.com`

3. `SMTP_PORT`
   - SMTP 端口。
   - 常用：`465`。
   - 如果不填，workflow 默认使用 `465`。

4. `SMTP_USERNAME`
   - 发件邮箱账号。

5. `SMTP_PASSWORD`
   - 发件邮箱的 SMTP 授权码或应用专用密码。
   - 不建议使用邮箱登录密码。

GitHub 设置入口：

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

相关 workflow：

- [[.github/workflows/daily-industry-news.yml]]
- [[.github/workflows/weekly-blog-topic-pool.yml]]
