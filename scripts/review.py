#!/usr/bin/env python3
"""
生成本地审核页面 - 浏览器打开即可观看视频并审批
用法: python scripts/review.py
"""

import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os

REPO_ROOT = Path(__file__).parent.parent
INDEX_FILE = REPO_ROOT / "index.json"
REVIEW_HTML = REPO_ROOT / "review.html"


def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(index):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def extract_bvid(url):
    for part in url.split("/"):
        if part.startswith("BV"):
            return part.split("?")[0]
    return None


def generate_html():
    index = load_index()
    pending = index.get("pending", [])

    if not pending:
        print("没有待审核的项目")
        return None

    items_html = ""
    for i, item in enumerate(pending):
        bvid = extract_bvid(item["url"])
        embed = ""
        if bvid:
            embed = f'<iframe src="https://player.bilibili.com/player.html?bvid={bvid}&autoplay=0" scrolling="no" frameborder="0" allowfullscreen="true" width="640" height="360"></iframe>'
        else:
            embed = f'<a href="{item["url"]}" target="_blank" class="link-btn">在平台打开</a>'

        dur = f"{item['duration']}s" if item.get("duration") else "未知"
        cats = ", ".join(item.get("categories", []))
        conf = item.get("confidence", "?")
        uploader = item.get("uploader", "未知")

        items_html += f'''
        <div class="card" id="card-{i}">
            <div class="video">{embed}</div>
            <div class="info">
                <h3>{item["title"]}</h3>
                <p>分类: <b>{cats}</b> | 时长: {dur} | 可信度: {conf} | 来源: {uploader}</p>
            </div>
            <div class="actions">
                <button class="btn approve" onclick="doAction({i}, 'approve')">批准</button>
                <button class="btn reject" onclick="doAction({i}, 'reject')">拒绝</button>
                <button class="btn skip" onclick="doAction({i}, 'skip')">跳过</button>
            </div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>公益广告审核</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f5f5f5; padding: 20px; }}
h1 {{ text-align: center; margin-bottom: 10px; color: #333; }}
.stats {{ text-align: center; margin-bottom: 20px; color: #666; }}
.card {{ background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.card.hidden {{ display: none; }}
.video {{ text-align: center; margin-bottom: 15px; }}
.video iframe {{ border-radius: 8px; }}
.video .link-btn {{ display: inline-block; padding: 10px 20px; background: #00a1d6; color: #fff; text-decoration: none; border-radius: 6px; }}
.info {{ margin-bottom: 15px; }}
.info h3 {{ font-size: 16px; color: #333; margin-bottom: 5px; }}
.info p {{ font-size: 13px; color: #888; }}
.actions {{ display: flex; gap: 10px; }}
.btn {{ padding: 8px 24px; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; color: #fff; }}
.btn.approve {{ background: #52c41a; }}
.btn.reject {{ background: #ff4d4f; }}
.btn.skip {{ background: #d9d9d9; color: #333; }}
.btn:hover {{ opacity: 0.85; }}
.done {{ text-align: center; padding: 40px; color: #52c41a; font-size: 20px; }}
</style>
</head>
<body>
<h1>公益广告审核</h1>
<div class="stats">待审核: <b id="count">{len(pending)}</b> 条</div>
{items_html}
<div class="done hidden" id="done">全部审核完成!</div>
<script>
let total = {len(pending)};
let reviewed = 0;
function doAction(i, action) {{
    fetch('/api/action', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{index: i, action: action}})
    }}).then(r => r.json()).then(d => {{
        if (d.ok) {{
            document.getElementById('card-' + i).classList.add('hidden');
            reviewed++;
            document.getElementById('count').textContent = total - reviewed;
            if (reviewed >= total) document.getElementById('done').classList.remove('hidden');
        }}
    }});
}}
</script>
</body>
</html>'''

    with open(REVIEW_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    return REVIEW_HTML


class ReviewHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/action":
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            idx = body["index"]
            action = body["action"]

            index = load_index()
            pending = index.get("pending", [])

            if 0 <= idx < len(pending):
                item = pending.pop(idx)
                if action == "approve":
                    item["status"] = "approved"
                    for cat in item.get("categories", []):
                        if cat in index["categories"]:
                            index["categories"][cat].append(item)
                save_index(index)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    html_path = generate_html()
    if not html_path:
        return

    os.chdir(REPO_ROOT)
    server = HTTPServer(("127.0.0.1", 8899), ReviewHandler)
    print(f"审核页面已启动: http://127.0.0.1:8899/{REVIEW_HTML.name}")
    print("按 Ctrl+C 停止")
    webbrowser.open(f"http://127.0.0.1:8899/{REVIEW_HTML.name}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        server.server_close()


if __name__ == "__main__":
    main()
