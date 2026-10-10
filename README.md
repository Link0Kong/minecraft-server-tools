# Minecraft 服务器工具集 (minecraft-server-tools)

一台自己维护的 Minecraft 服务器的「运维周边」：本地管理面板、按需启停、DDNS 自动解析、启动入口页。

> 服务器本体（NeoForge + 模组 + 语音）不在这个仓库里，这里只放周边脚本。

## 组成

| 目录 / 文件 | 作用 |
|---|---|
| `mc_dashboard.py` | 本地管理面板（Flask）：在线玩家、系统状态、事件日志、模组启停、RCON 控制台、启停/重启按钮 |
| `panel/index.html` | 面板前端（独立文件，避免 Python 里的转义地狱） |
| `启动MC面板.bat` / `launch_mc_panel.vbs` | 双击启动面板（VBS 负责隐藏控制台窗口） |
| `mc_ssh.py` | 用 paramiko 跑一条远程命令（省得每次手敲 ssh） |
| `mc_status.py` | 查 ECS 实例状态（只读） |
| `mc_ping_now.py` | 探活 / 查看在线人数 |
| `start_mc.py` | 触发 ECS 开机 |
| `update_dns.py` + `ddns-update.{service,timer}` | 公网 IP 变了就自动更新域名 A 记录（systemd timer 每分钟跑） |
| `deploy_mc.sh` | 部署脚本 |
| `start-worker/` | Cloudflare Worker：一键启动入口（代理到云函数，剥掉 `Content-Disposition` 让浏览器直接显示） |
| `start-page/` | 启动页 HTML（备用的静态版本） |
| `config.json.template` | DDNS 配置模板 |

## 设计取舍

- **按需启停**：玩家点一下链接 → 云函数调 ECS 开机；服务器内 cron 每分钟查 RCON 在线人数，**无人在线 10 分钟** 就 `save-all` + 停机，省电费。
- **NAT 环境下的语音**：ECS 是 NAT，`voice_host` 必须显式写成域名，否则客户端会连到内网 IP。
- **DDNS**：公网 IP 会变，所以域名解析交给 systemd timer 每分钟同步一次。

## 使用前

1. 复制 `config.json.template` 为 `config.json`，填入你自己的阿里云 AccessKey 与域名。
2. 面板口令、RCON 口令、SSH 口令请用环境变量注入（本仓库中的占位符不是可用凭据）。
3. `start-worker` 需要 `wrangler secret put FC_TOKEN` 注入云函数 token。

## 许可

MIT
