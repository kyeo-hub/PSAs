#!/usr/bin/env python3
"""
按分类批量下载公益广告视频
用法: python scripts/download.py <分类名>
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_FILE = REPO_ROOT / "index.json"
OUTPUT_DIR = REPO_ROOT / "output"


def download(category):
    if not INDEX_FILE.exists():
        print("index.json 不存在，请先运行收集脚本")
        return

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    if category not in index["categories"]:
        print(f"未知分类: {category}")
        print(f"可用分类: {', '.join(index['categories'].keys())}")
        return

    entries = index["categories"][category]
    if not entries:
        print(f"分类 '{category}' 暂无视频")
        return

    out = OUTPUT_DIR / category
    out.mkdir(parents=True, exist_ok=True)

    print(f"准备下载 {len(entries)} 个视频到 {out}")
    for i, entry in enumerate(entries, 1):
        url = entry["url"]
        title = entry["title"].replace("/", "_").replace("\\", "_")
        print(f"\n[{i}/{len(entries)}] {entry['title']}")

        cmd = [
            "yt-dlp",
            url,
            "-o", str(out / f"{title}.%(ext)s"),
            "--no-overwrites",
        ]
        try:
            subprocess.run(cmd, timeout=300)
        except subprocess.TimeoutExpired:
            print(f"  超时跳过: {url}")
        except Exception as e:
            print(f"  下载失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/download.py <分类名>")
        print("示例: python scripts/download.py 文明礼貌")
        sys.exit(1)

    download(sys.argv[1])
