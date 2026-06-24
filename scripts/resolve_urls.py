#!/usr/bin/env python3
"""
解析公益广告的真实播放地址
从 index.json 的 play_url 提取 HLS 流地址，更新到 ads.json
"""

import json
import subprocess
import sys
import time
import random
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_FILE = REPO_ROOT / "index.json"
ADS_FILE = REPO_ROOT / "docs" / "api" / "ads.json"


def resolve_url(play_url):
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--socket-timeout", "15",
        play_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None, None
        data = json.loads(result.stdout.strip())
        video_url = data.get("url", "")
        formats = data.get("formats", [])
        best_url = video_url
        for fmt in formats:
            if fmt.get("protocol") == "m3u8_native":
                best_url = fmt.get("url", video_url)
                break
        return best_url, data.get("duration")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None, None


def main():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    pending = index.get("pending", [])
    total = len(pending)
    resolved = 0
    failed = 0
    skipped = 0

    print(f"共 {total} 条待解析\n")

    ads_items = []
    for i, entry in enumerate(pending):
        play_url = entry.get("url", "")
        if not play_url:
            skipped += 1
            continue

        print(f"[{i+1}/{total}] {entry.get('id', '')} {entry.get('title', '')}", end=" ... ", flush=True)

        video_url, duration = resolve_url(play_url)
        if video_url:
            if video_url.startswith("http://"):
                video_url = video_url.replace("http://", "https://", 1)
            resolved += 1
            print(f"OK ({video_url[:60]}...)")
        else:
            failed += 1
            print("FAIL")

        categories = entry.get("categories", ["未分类"])
        if categories == ["未分类"]:
            categories = ["综合"]

        ads_items.append({
            "id": entry.get("id", ""),
            "title": entry.get("title", ""),
            "categories": categories,
            "duration": duration or entry.get("duration", 30),
            "url": video_url or entry.get("download_url", ""),
            "play_url": play_url,
            "thumbnail": entry.get("thumbnail", ""),
            "source": entry.get("platform", "unknown"),
            "uploader": entry.get("uploader", ""),
        })

        time.sleep(random.uniform(0.5, 2))

    cat_summary = {}
    for item in ads_items:
        for cat in item["categories"]:
            cat_summary[cat] = cat_summary.get(cat, 0) + 1

    ads = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(ads_items),
        "resolved": resolved,
        "failed": failed,
        "categories_summary": dict(sorted(cat_summary.items(), key=lambda x: -x[1])),
        "items": ads_items,
    }

    ADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ADS_FILE, "w", encoding="utf-8") as f:
        json.dump(ads, f, ensure_ascii=False, indent=2)

    print(f"\n完成: 成功 {resolved}, 失败 {failed}, 跳过 {skipped}")
    print(f"输出: {ADS_FILE}")


if __name__ == "__main__":
    main()
