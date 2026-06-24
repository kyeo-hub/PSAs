#!/usr/bin/env python3
"""
从央视公益广告作品库 (igongyi.cntv.cn) 抓取全部公益广告元数据
API: http://app1.vote.cntv.cn/viewVoteAction.do?voteId=13488&type=json
"""

import json
import re
import sys
import time
import random
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_FILE = REPO_ROOT / "index.json"
CNTV_API = "http://app1.vote.cntv.cn/viewVoteAction.do?voteId=13488&type=json"


def load_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            index = json.load(f)
        index.setdefault("categories", {k: [] for k in CATEGORY_KEYWORDS})
        index.setdefault("pending", [])
        index.setdefault("collected_urls", [])
        return index
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


CATEGORY_KEYWORDS = {
    "文明礼貌": ["文明", "礼貌", "礼仪", "尊重", "谦让", "排队", "礼让", "公德", "礼", "德"],
    "孝道": ["孝", "父母", "老人", "尊老", "亲情", "陪伴", "家庭", "家风", "慈母", "报恩", "入则孝", "百善孝"],
    "节约": ["节约", "光盘", "节水", "节电", "浪费", "粮食", "勤俭", "节俭", "俭", "勤"],
    "环保": ["环保", "环境", "地球", "垃圾", "绿色", "生态", "低碳", "水", "森林", "青山", "绿水", "湿地"],
    "交通安全": ["交通", "安全出行", "红绿灯", "斑马线", "酒驾", "行车", "安全", "驾驶", "超速"],
    "禁烟": ["禁烟", "吸烟", "烟草", "二手烟", "戒烟"],
    "诚信": ["诚信", "诚实", "守信", "信用", "信任", "真诚", "纳税", "廉"],
    "友善": ["友善", "友爱", "团结", "互助", "关爱", "和谐", "和为贵", "善", "仁"],
    "爱国": ["爱国", "祖国", "国旗", "国歌", "民族", "核心价值", "中国梦", "中国", "中华", "国泰"],
    "助人为乐": ["助人", "帮助", "志愿", "奉献", "雷锋", "公益行动"],
}

# 古诗词/成语风格的标题额外匹配
PHRASE_CATEGORY_MAP = {
    "和满中华": ["友善", "爱国"],
    "勤善和谐": ["友善", "节约"],
    "德大人吉祥": ["文明礼貌"],
    "与人为善": ["友善"],
    "己所不欲": ["文明礼貌"],
    "勿以善小": ["助人为乐"],
    "天下兴亡": ["爱国"],
    "饮水思源": ["孝道", "环保"],
    "百善孝为先": ["孝道"],
    "入则孝出则悌": ["孝道"],
    "静以修身": ["文明礼貌"],
    "俭以养德": ["节约"],
    "仁者爱人": ["友善"],
    "源洁则流清": ["环保"],
    "克己复礼": ["文明礼貌"],
    "吾日三省": ["诚信"],
    "满招损谦受益": ["文明礼貌"],
    "勤俭持家": ["节约"],
    "劳动光荣": ["节约"],
    "劳动最美": ["节约"],
    "劳动创造": ["节约"],
    "民吾同胞": ["友善"],
    "兼相爱": ["友善"],
    "天地水美山青": ["环保"],
    "绿水青山": ["环保"],
    "日三省吾身": ["诚信"],
    "直心为德": ["诚信"],
    "德者性之端": ["诚信"],
    "近者亲其善": ["友善"],
    "播种善良": ["助人为乐"],
    "肩挑勤与善": ["节约", "友善"],
    "种树": ["环保"],
    "中华有福": ["爱国"],
    "中国日子": ["爱国"],
    "中国向上": ["爱国"],
    "花开中国梦": ["爱国"],
    "圆梦": ["爱国"],
    "红日映中国": ["爱国"],
    "锦绣中华": ["爱国"],
    "祖国和谐": ["爱国", "友善"],
    "祖国山水": ["爱国", "环保"],
    "百姓日子": ["爱国"],
    "福入家门": ["节约"],
    "节俭者": ["节约"],
    "勤俭持家": ["节约"],
    "助人为乐": ["助人为乐"],
    "助人有福": ["助人为乐"],
    "香在人间": ["助人为乐"],
    "人间大美": ["助人为乐"],
    "友邻是福": ["友善"],
    "行善是福": ["助人为乐"],
    "孝老是福": ["孝道"],
    "节俭是福": ["节约"],
    "善作魂": ["友善"],
    "诚立身": ["诚信"],
    "孝当先": ["孝道"],
    "勤为本": ["节约"],
    "俭养德": ["节约"],
    "国是家": ["爱国"],
    "和为贵": ["友善"],
    "勤善为本": ["节约", "友善"],
    "崇德向善": ["友善"],
    "吉祥满天": ["友善"],
    "得蛙蛙": ["文明礼貌"],
    "讲文明树新风": ["文明礼貌"],
    "最美的风景叫文明": ["文明礼貌"],
    "文明中国人": ["文明礼貌", "爱国"],
    "文明出行": ["文明礼貌", "交通安全"],
    "文明旅游": ["文明礼貌"],
    "文明出游": ["文明礼貌"],
    "文明用餐": ["文明礼貌"],
    "垃圾分类": ["环保"],
    "低碳生活": ["环保"],
    "绿色出行": ["环保"],
    "绿色生活": ["环保"],
    "节约用": ["节约"],
    "珍惜粮食": ["节约"],
    "反对浪费": ["节约"],
    "食品安全": ["交通安全"],
    "防灾知识": ["交通安全"],
    "应急救护": ["交通安全"],
    "消防安全": ["交通安全"],
    "防震": ["交通安全"],
    "防洪": ["交通安全"],
    "禁毒": ["禁烟"],
    "毒品": ["禁烟"],
    "网络安全": ["交通安全"],
    "防诈骗": ["交通安全"],
    "中国梦": ["爱国"],
    "二十四节气": ["爱国"],
    "长城谣": ["爱国"],
    "勿忘国耻": ["爱国"],
    "抗战": ["爱国"],
    "健康中国": ["爱国"],
    "爱国": ["爱国"],
    "敬业": ["文明礼貌"],
    "自由": ["爱国"],
    "民主": ["爱国"],
    "富强": ["爱国"],
    "平等": ["友善"],
    "公正": ["诚信"],
    "法制": ["爱国"],
    "和谐": ["友善"],
    "社会主义核心价值观": ["爱国", "友善", "诚信"],
    "家国梦": ["爱国"],
    "陪伴": ["孝道"],
    "关爱老人": ["孝道", "友善"],
    "关爱家人": ["孝道", "友善"],
    "留守儿童": ["友善"],
    "关爱留守": ["友善"],
    "空巢": ["孝道"],
    "善待明天": ["友善"],
    "器官捐献": ["助人为乐"],
    "献血": ["助人为乐"],
    "献爱心": ["助人为乐"],
    "见义勇为": ["助人为乐"],
    "学雷锋": ["助人为乐"],
    "志愿者": ["助人为乐"],
    "让座": ["文明礼貌"],
    "升旗": ["爱国"],
    "保护动物": ["环保"],
    "保护江豚": ["环保"],
    "保护森林": ["环保"],
    "保护湿地": ["环保"],
    "保护海洋": ["环保"],
    "保护环境": ["环保"],
    "保护版权": ["文明礼貌"],
    "保护知识产权": ["文明礼貌"],
    "节能减排": ["环保", "节约"],
    "野生救援": ["环保"],
    "蓝天保卫战": ["环保"],
    "蓝天": ["环保"],
    "沙尘": ["环保"],
    "二氧化碳": ["环保"],
    "水土流失": ["环保"],
    "生物多样性": ["环保"],
    "少开车": ["环保"],
    "低碳开车": ["环保"],
    "勤学向上": ["文明礼貌"],
    "读书": ["文明礼貌"],
    "阅读": ["文明礼貌"],
    "推广普通话": ["文明礼貌"],
    "诚信纳税": ["诚信"],
    "诚信是福": ["诚信"],
    "诚信美德": ["诚信"],
    "诚信助推": ["诚信", "爱国"],
    "反腐倡廉": ["诚信"],
    "举报贪腐": ["诚信"],
    "廉洁": ["诚信"],
    "广而兼是为廉": ["诚信"],
    "正确使用权利": ["诚信"],
    "依法经营": ["诚信"],
    "税收": ["诚信"],
    "营改增": ["诚信"],
    "办税": ["诚信"],
    "绿水青山就是金山银山": ["环保"],
}


def classify(title):
    matched = set()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                matched.add(category)
                break

    for phrase, cats in PHRASE_CATEGORY_MAP.items():
        if phrase in title:
            matched.update(cats)

    return list(matched) if matched else ["未分类"]


def fetch_cntv_data():
    req = urllib.request.Request(CNTV_API, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://igongyi.cntv.cn/",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    m = re.search(r'var\s+voteJson13488\s*=\s*(\{.*\})\s*;?\s*$', raw, re.DOTALL)
    if not m:
        print("无法解析 API 返回数据", file=sys.stderr)
        return []

    data = json.loads(m.group(1))
    items = data.get("voteItems", [])

    videos = []
    for i in range(0, len(items) - 1, 2):
        play_item = items[i]
        dl_item = items[i + 1]

        show_name = play_item.get("showName", "")
        parts = show_name.split("#")
        title = parts[0] if len(parts) > 0 else ""
        source = parts[1] if len(parts) > 1 else ""
        duration_str = parts[2] if len(parts) > 2 else ""
        play_url = parts[3] if len(parts) > 3 else play_item.get("nameLink", "")

        dur_seconds = None
        if duration_str:
            m_dur = re.match(r'(\d+)(?:s|秒)?', duration_str)
            if m_dur:
                dur_seconds = int(m_dur.group(1))

        download_url = dl_item.get("nameLink", "")
        code = play_item.get("name", "")

        if not title:
            continue

        videos.append({
            "title": title,
            "source": source,
            "code": code,
            "play_url": play_url,
            "download_url": download_url,
            "duration": dur_seconds,
            "duration_str": duration_str,
            "thumbnail": play_item.get("imageUrl", ""),
            "view_count": play_item.get("voteNum", 0),
        })

    return videos


def main():
    print("正在从央视公益广告作品库获取数据...")
    videos = fetch_cntv_data()
    print(f"共获取 {len(videos)} 部公益广告\n")

    index = load_index()
    collected_urls = set(index.get("collected_urls", []))
    new_count = 0

    for v in videos:
        url = v["play_url"]
        if url in collected_urls:
            continue

        categories = classify(v["title"])
        entry = {
            "title": v["title"],
            "url": url,
            "id": v["code"],
            "duration": v["duration"],
            "duration_str": v["duration_str"],
            "uploader": v["source"],
            "view_count": v["view_count"],
            "thumbnail": v["thumbnail"],
            "download_url": v["download_url"],
            "platform": "cntv",
            "categories": categories,
            "confidence": "high",
            "status": "pending",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

        index["pending"].append(entry)
        collected_urls.add(url)
        new_count += 1
        print(f"  [{new_count}] {v['code']} {v['title']} ({v['source']}, {v['duration_str']}) -> {categories}")

    index["collected_urls"] = list(collected_urls)
    save_index(index)

    total = len(index["collected_urls"])
    pending = len(index.get("pending", []))
    print(f"\n完成: 新增 {new_count} 条, 总计 {total} 条, 待审核 {pending} 条")


if __name__ == "__main__":
    main()
