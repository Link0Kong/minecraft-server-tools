// MC 服务器启动入口 Worker
// 作用：代理到 FC 函数，剥掉 Content-Disposition: attachment，让浏览器正常显示页面
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 首页：启动按钮
    if (path === "/" || path === "/index.html") {
      return new Response(LANDING, {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    // 启动接口：代理到 FC 函数
    if (path === "/start") {
      const token = (env.FC_TOKEN || "").trim();
      const fcUrl =
        "https://mc-start-mc-serv-control-alwwvseret.cn-hangzhou.fcapp.run/?token=" +
        encodeURIComponent(token);
      try {
        const resp = await fetch(fcUrl);
        const body = await resp.text();
        // 关键：重新设置响应头，去掉 Content-Disposition: attachment
        const headers = new Headers();
        headers.set("Content-Type", "text/html; charset=utf-8");
        return new Response(body, { status: resp.status, headers });
      } catch (e) {
        return new Response(ERR_HTML(String(e && e.message || e)), {
          status: 500,
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      }
    }

    return new Response("Not Found", { status: 404 });
  },
};

const LANDING = `<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MC 服务器启动</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#1e293b;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{background:#334155;border-radius:16px;padding:48px 56px;text-align:center;max-width:420px;box-shadow:0 10px 40px rgba(0,0,0,.4)}
h1{margin:0 0 8px;font-size:26px}
p{margin:0 0 28px;color:#94a3b8;font-size:15px;line-height:1.6}
button{background:#38bdf8;border:none;color:#0f172a;font-size:17px;font-weight:600;padding:14px 40px;border-radius:12px;cursor:pointer}
button:hover{background:#7dd3fc}
.hint{margin-top:20px;font-size:12px;color:#64748b}
</style></head><body>
<div class="card"><h1>🕹️ Minecraft 服务器</h1>
<p>点击下方按钮启动服务器，约 3-5 分钟后即可连接 <code>mc.furina.fun</code></p>
<button onclick="location.href='/start'">启动服务器</button>
<p class="hint">无人在线 10 分钟后会自动节省停机</p></div>
</body></html>`;

const ERR_HTML = (msg) => `<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"></head>
<body style="font-family:sans-serif;background:#1e293b;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh">
<div style="background:#334155;border-radius:16px;padding:40px;text-align:center">
<h1>启动失败</h1><p style="color:#94a3b8">${msg}</p></div>
</body></html>`;
