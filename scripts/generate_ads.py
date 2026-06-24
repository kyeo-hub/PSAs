#!/usr/bin/env python3
"""
将 index.json 转换为 ads.json API 格式
生成供 TVBox 自定义壳使用的广告数据源
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_FILE = REPO_ROOT / "index.json"
ADS_FILE = REPO_ROOT / "docs" / "api" / "ads.json"
CONFIG_FILE = REPO_ROOT / "docs" / "api" / "ad_config.json"


def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_ads_json(index):
    items = []
    seen_ids = set()

    all_entries = index.get("pending", [])
    for entry in all_entries:
        if entry.get("status") == "rejected":
            continue

        entry_id = entry.get("id", "")
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)

        categories = entry.get("categories", ["未分类"])
        if categories == ["未分类"]:
            categories = ["综合"]

        duration = entry.get("duration")
        if duration is None:
            duration = 30

        download_url = entry.get("download_url", "")
        play_url = entry.get("url", "")

        stream_url = download_url if download_url else play_url

        items.append({
            "id": entry_id,
            "title": entry.get("title", ""),
            "categories": categories,
            "duration": duration,
            "url": stream_url,
            "play_url": play_url,
            "thumbnail": entry.get("thumbnail", ""),
            "source": entry.get("platform", "unknown"),
            "uploader": entry.get("uploader", ""),
            "view_count": entry.get("view_count", 0),
        })

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "categories_summary": {},
        "items": items,
    }


def build_config_json():
    return {
        "ads": {
            "source": {
                "type": "api",
                "url": "https://kyeo-hub.github.io/PSAs/api/ads.json",
                "refresh_interval": 3600,
            },
            "rules": {
                "pre_roll": {
                    "enabled": True,
                    "probability": 1.0,
                    "max_duration": 60,
                    "skip_after": 5,
                },
                "mid_roll": {
                    "enabled": True,
                    "probability": 0.3,
                    "min_video_duration": 600,
                    "trigger_percent": [30, 60],
                    "max_duration": 30,
                },
            },
            "scheduling": {
                "strategy": "round_robin",
                "weight_by_category": {
                    "环保": 1,
                    "文明礼貌": 1,
                    "爱国": 1,
                    "孝道": 1,
                    "节约": 1,
                    "交通安全": 1,
                    "诚信": 1,
                    "友善": 1,
                    "助人为乐": 1,
                    "禁烟": 1,
                    "综合": 1,
                },
                "avoid_repeat_hours": 24,
                "daily_max_impressions": 20,
            },
            "display": {
                "show_title": True,
                "show_category_tag": True,
                "countdown": True,
                "skip_button_text": "跳过广告",
            },
        }
    }


def main():
    index = load_index()
    ads = build_ads_json(index)

    cat_summary = {}
    for item in ads["items"]:
        for cat in item["categories"]:
            cat_summary[cat] = cat_summary.get(cat, 0) + 1
    ads["categories_summary"] = dict(sorted(cat_summary.items(), key=lambda x: -x[1]))

    config = build_config_json()

    ADS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(ADS_FILE, "w", encoding="utf-8") as f:
        json.dump(ads, f, ensure_ascii=False, indent=2)
    print(f"生成: {ADS_FILE} ({ads['total']} 条)")

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"生成: {CONFIG_FILE}")

    print(f"\n分类统计:")
    for cat, count in ads["categories_summary"].items():
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
