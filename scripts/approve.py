#!/usr/bin/env python3
"""
审核脚本 - 将待审核的公益广告移入正式分类
用法:
  python scripts/approve.py list              # 列出待审核项
  python scripts/approve.py approve <序号>     # 批准某条
  python scripts/approve.py approve all        # 批准全部
  python scripts/approve.py reject <序号>      # 拒绝某条
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_FILE = REPO_ROOT / "index.json"


def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(index):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def list_pending():
    index = load_index()
    pending = index.get("pending", [])
    if not pending:
        print("没有待审核的项目")
        return

    print(f"待审核: {len(pending)} 条\n")
    for i, item in enumerate(pending):
        dur = f"{item['duration']}s" if item.get("duration") else "未知"
        conf = item.get("confidence", "?")
        cats = ", ".join(item.get("categories", []))
        print(f"  [{i}] {item['title']}")
        print(f"      分类: {cats} | 时长: {dur} | 可信度: {conf}")
        print(f"      来源: {item.get('uploader', '未知')} | {item['url']}")
        print()


def approve(index, i):
    pending = index.get("pending", [])
    if i < 0 or i >= len(pending):
        print(f"序号 {i} 超出范围 (0-{len(pending)-1})")
        return False

    item = pending.pop(i)
    item["status"] = "approved"
    for cat in item.get("categories", []):
        if cat in index["categories"]:
            index["categories"][cat].append(item)
    print(f"已批准: {item['title']}")
    return True


def reject(index, i):
    pending = index.get("pending", [])
    if i < 0 or i >= len(pending):
        print(f"序号 {i} 超出范围 (0-{len(pending)-1})")
        return False

    item = pending.pop(i)
    print(f"已拒绝: {item['title']}")
    return True


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python scripts/approve.py list")
        print("  python scripts/approve.py approve <序号|all>")
        print("  python scripts/approve.py reject <序号>")
        return

    cmd = sys.argv[1]
    index = load_index()

    if cmd == "list":
        list_pending()

    elif cmd == "approve":
        if len(sys.argv) < 3:
            print("用法: python scripts/approve.py approve <序号|all>")
            return
        arg = sys.argv[2]
        if arg == "all":
            count = len(index.get("pending", []))
            for _ in range(count):
                approve(index, 0)
            save_index(index)
            print(f"\n已批准全部 {count} 条")
        else:
            if approve(index, int(arg)):
                save_index(index)

    elif cmd == "reject":
        if len(sys.argv) < 3:
            print("用法: python scripts/approve.py reject <序号>")
            return
        if reject(index, int(sys.argv[2])):
            save_index(index)

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
