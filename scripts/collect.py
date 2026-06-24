#!/usr/bin/env python3
"""
公益广告自动收集脚本
- 从B站等平台搜索公益广告
- 多层质量过滤：来源白名单 + 时长过滤 + 关键词过滤
- 增量更新，避免重复
- 收集到待审核区，人工确认后入正式库
"""

import json
import os
import subprocess
import sys
import time
import random
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_FILE = REPO_ROOT / "index.json"

# 搜索关键词，越精确越好
SEARCH_KEYWORDS = [
    "央视公益广告",
    "经典公益广告 传统美德",
    "公益广告 文明",
    "公益广告 孝道",
    "公益广告 节约粮食",
    "公益广告 环保",
    "公益广告 交通安全",
    "公益广告 诚信",
    "公益广告 友善",
    "公益广告 爱国",
    "弘扬中华传统美德 公益广告",
    "社会主义核心价值观 公益",
    "讲文明树新风 公益广告",
    "央视 公益 合集",
    "文明中国 公益",
]

# 来源白名单：优先收录的频道/账号关键词
TRUSTED_UPLOADERS = [
    "央视", "CCTV", "cctv",
    "文明中国", "中国文明网",
    "各省卫视", "湖南卫视", "浙江卫视", "东方卫视",
    "人民日报", "新华社", "新华网",
    "学习强国", "共青团",
    "公益广告", "公益",
    "文明", "精神文明",
]

# 标题必须包含至少一个（核心词）
TITLE_WHITELIST = [
    "公益广告", "公益", "广告",
    "传统美德", "文明", "美德",
    "社会主义核心价值观",
    "讲文明", "树新风", "弘扬",
    "节约", "环保", "交通安全",
    "禁烟", "诚信", "友善", "爱国",
    "孝", "尊老", "助人为乐",
]

# 标题包含这些词直接排除
TITLE_BLACKLIST = [
    "搞笑", "鬼畜", "混剪", "盘点", "合集解说",
    "吐槽", "沙雕", "整活", "恶搞", "模仿",
    "翻唱", "翻拍", "二创", "反应", "测评",
    "vlog", "VLOG", "直播",
]

# 分类关键词
CATEGORY_KEYWORDS = {
    "文明礼貌": ["文明", "礼貌", "礼仪", "尊重", "谦让", "排队"],
    "孝道": ["孝", "父母", "老人", "尊老", "亲情", "陪伴"],
    "节约": ["节约", "光盘", "节水", "节电", "浪费", "粮食"],
    "环保": ["环保", "环境", "地球", "垃圾", "绿色", "生态"],
    "交通安全": ["交通", "安全", "红绿灯", "斑马线", "酒驾"],
    "禁烟": ["禁烟", "吸烟", "烟草", "二手烟", "戒烟"],
    "诚信": ["诚信", "诚实", "守信", "信用", "信任"],
    "友善": ["友善", "友爱", "团结", "互助", "关爱"],
    "爱国": ["爱国", "祖国", "国旗", "国歌", "民族"],
    "助人为乐": ["助人", "帮助", "志愿", "奉献", "雷锋"],
}

# 时长限制（秒）
DURATION_MIN = 10
DURATION_MAX = 300


def load_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "categories": {k: [] for k in CATEGORY_KEYWORDS},
        "pending": [],
        "collected_urls": [],
        "last_updated": None,
    }


def save_index(index):
    index["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def check_uploader_trusted(uploader):
    if not uploader:
        return False
    return any(t in uploader for t in TRUSTED_UPLOADERS)


def check_title_valid(title):
    if not title:
        return False, "标题为空"
    lower = title.lower()
    for kw in TITLE_BLACKLIST:
        if kw.lower() in lower:
            return False, f"命中黑名单: {kw}"
    has_whitelist = any(kw in title for kw in TITLE_WHITELIST)
    if not has_whitelist:
        return False, "未命中白名单关键词"
    return True, "通过"


def check_duration(duration):
    if duration is None:
        return True, "时长未知，放行待审"
    if duration < DURATION_MIN:
        return False, f"时长过短: {duration}s"
    if duration > DURATION_MAX:
        return False, f"时长过长: {duration}s"
    return True, "通过"


def classify(title, description=""):
    text = title + " " + description
    matched = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                matched.append(category)
                break
    return matched if matched else ["未分类"]


def filter_video(video):
    title = video["title"]
    uploader = video.get("uploader", "")
    duration = video.get("duration")

    title_ok, title_reason = check_title_valid(title)
    if not title_ok:
        return False, title_reason

    dur_ok, dur_reason = check_duration(duration)
    if not dur_ok:
        return False, dur_reason

    uploader_trusted = check_uploader_trusted(uploader)

    categories = classify(title, video.get("description", ""))

    if "未分类" in categories and not uploader_trusted:
        return False, "无法分类且来源不可信"

    confidence = "high" if uploader_trusted else "medium"
    if dur_ok and duration is None:
        confidence = "low"

    return True, {
        "categories": categories,
        "confidence": confidence,
        "uploader_trusted": uploader_trusted,
    }


def search_bilibili(keyword, max_results=5):
    cmd = [
        "yt-dlp",
        f"bilisearch{max_results}:{keyword}",
        "--flat-playlist",
        "--dump-json",
        "--no-download",
        "--no-warnings",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                videos.append({
                    "title": data.get("title", ""),
                    "url": data.get("url") or data.get("webpage_url") or f"https://www.bilibili.com/video/{data.get('id', '')}",
                    "id": data.get("id", ""),
                    "duration": data.get("duration"),
                    "description": data.get("description", ""),
                    "uploader": data.get("uploader", ""),
                    "view_count": data.get("view_count"),
                    "platform": "bilibili",
                })
            except json.JSONDecodeError:
                continue
        return videos
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"  搜索失败: {e}", file=sys.stderr)
        return []


def collect(max_per_keyword=5, total_limit=10):
    index = load_index()
    collected_urls = set(index.get("collected_urls", []))
    new_count = 0
    skip_count = 0

    keywords = list(SEARCH_KEYWORDS)
    random.shuffle(keywords)

    for keyword in keywords:
        if new_count >= total_limit:
            break

        print(f"搜索: {keyword}")
        videos = search_bilibili(keyword, max_results=max_per_keyword)

        for video in videos:
            if new_count >= total_limit:
                break

            url = video["url"]
            if url in collected_urls:
                continue

            passed, result = filter_video(video)
            if not passed:
                skip_count += 1
                print(f"  [跳过] {video['title']} - {result}")
                continue

            categories = result["categories"]
            confidence = result["confidence"]
            entry = {
                "title": video["title"],
                "url": url,
                "id": video["id"],
                "duration": video["duration"],
                "uploader": video["uploader"],
                "view_count": video["view_count"],
                "platform": video["platform"],
                "categories": categories,
                "confidence": confidence,
                "status": "pending",
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }

            index["pending"].append(entry)
            collected_urls.add(url)
            index["collected_urls"] = list(collected_urls)
            new_count += 1
            print(f"  [待审 {new_count}] {video['title']} -> {categories} (可信度: {confidence})")

        delay = random.uniform(10, 25)
        print(f"  等待 {delay:.0f}s...")
        time.sleep(delay)

    save_index(index)
    total = len(index["collected_urls"])
    pending = len(index.get("pending", []))
    print(f"\n完成: 新增 {new_count} 条待审, 跳过 {skip_count} 条, 总计 {total} 条, 待审核 {pending} 条")
    return new_count


if __name__ == "__main__":
    limit = int(os.environ.get("COLLECT_LIMIT", "10"))
    collect(total_limit=limit)
