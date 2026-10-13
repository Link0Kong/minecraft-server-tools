#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键启动 Minecraft 服务器（走阿里云函数计算 FC，国内直连，无需翻墙）"""
import os
import urllib.request

TOKEN = os.environ.get("MC_START_TOKEN", "")
URL = ("https://mc-start-mc-serv-control-alwwvseret.cn-hangzhou.fcapp.run/"
       "?token=" + TOKEN)


def main():
    print("正在联系服务器...")
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            html = resp.read().decode("utf-8", "replace")

        if "已在运行" in html:
            print("\n[OK] 服务器已在运行，直接连接 mc.furina.fun 即可")
        elif "正在启动" in html:
            print("\n[OK] 正在启动服务器，请等 1-3 分钟后连接 mc.furina.fun")
        elif "token" in html.lower():
            print("\n[错误] token 无效")
        else:
            print("\n状态：", html[:300])
    except Exception as e:
        print("\n[失败] 请求出错:", e)

    print("\n(窗口可关闭)")


if __name__ == "__main__":
    main()
