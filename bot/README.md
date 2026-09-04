# GachaClock 微信机器人

该目录提供 NoneBot2 与 ClawWeixin 适配器的常驻进程。机器人从 GachaClock 线上静态数据读取当前卡池，支持“卡池”和“卡池 游戏名”私聊命令，不会自动发起微信扫码登录。

## 本地安装

```powershell
cd bot
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m gachaclock_bot
```

## 卡池命令

```text
卡池
卡池 原神
卡池 崩铁
卡池 绝区零
卡池 鸣潮
卡池 方舟
卡池 终末地
```

## 微信登录

在部署终端执行适配器提供的登录命令：

```bash
.venv/bin/claweixin-login
```

扫码成功后，将输出的 Token 写入部署机的 `.env`，不得提交到 Git。机器人采用长轮询，需要常驻运行；GitHub Actions 只继续负责卡池数据和网页部署。

## 常驻运行

服务器使用 `deploy/gachaclock-bot.service` 注册 systemd 服务：

```bash
systemctl enable --now gachaclock-bot
systemctl status gachaclock-bot
journalctl -u gachaclock-bot -f
```
