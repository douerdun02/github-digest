#!/usr/bin/env python3
"""GitHub Daily Digest - Server酱 Push Module
通过 Server酱推送每日摘要到微信（支持多用户 SendKey）
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

SERVERCHAN_URL = "https://sctapi.ftqq.com/{key}.send"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_message(data):
    """构建推送消息内容"""
    today = data.get("date", "")
    summary = data.get("summary", {})
    by_category = data.get("by_category", {})
    total = data.get("total", 0)

    # 生成每日摘要标题
    title = f"GitHub 摘要 {today}"

    # 构建 Markdown 格式内容
    lines = [
        f"## GitHub 摘要大全 · {today}",
        "",
        f"**共收录 {total} 条内容** · AI 相关 {summary.get('ai_related', 0)} 条 · 数据开发 {summary.get('data_related', 0)} 条",
        "",
        "---",
    ]

    # 中文文章动态
    chinese_articles = data.get("chinese_articles", [])
    if chinese_articles:
        lines.append("### 📝 中文文章动态")
        for item in chinese_articles[:5]:
            name = item.get("name", "")
            lines.append(f"- [{name}]({item.get('url', '#')})")
        lines.append("")

    # 作者推荐
    author_recommends = data.get("author_recommends", [])
    if author_recommends:
        lines.append("### 👤 中文作者推荐")
        for item in author_recommends[:5]:
            name = item.get("name", "")
            source = item.get("source", "")
            lines.append(f"- [{name}]({item.get('url', '#')}) — {source}")
        lines.append("")

    # 中文热门项目
    chinese_picks = data.get("chinese_picks", [])
    if chinese_picks:
        lines.append("### 🇨🇳 中文热门项目")
        for item in chinese_picks[:5]:
            name = item.get("name", "")
            stars = item.get("stars", "")
            cn_trans = item.get("_cn_translate", "")
            desc = cn_trans or item.get("description", "")[:60]
            lines.append(f"- [{name}]({item.get('url', '#')}) ★{stars} - {desc}")
        lines.append("")

    # 资源合集推荐
    chinese_resources = data.get("chinese_resources", [])
    if chinese_resources:
        lines.append("### 📚 资源合集推荐")
        for item in chinese_resources[:3]:
            name = item.get("name", "")
            stars = item.get("stars", "")
            lines.append(f"- [{name}]({item.get('url', '#')}) ★{stars}")
        lines.append("")

    # 热门 Trending
    trending = data.get("trending", [])
    if trending:
        lines.append("### 🔥 今日热门")
        for item in trending[:5]:
            name = item.get("name", "")
            stars = item.get("stars", "")
            cn_trans = item.get("_cn_translate", "")
            desc = cn_trans or item.get("description", "")[:60]
            lines.append(f"- [{name}]({item.get('url', '#')}) ★{stars} - {desc}")
        lines.append("")

    # AI 相关
    ai_focus = data.get("ai_focus", [])
    if ai_focus:
        lines.append("### 🤖 AI 相关项目")
        for item in ai_focus[:5]:
            name = item.get("name", "")
            stars = item.get("stars", "")
            cn_trans = item.get("_cn_translate", "")
            desc = cn_trans or item.get("description", "")[:60]
            lines.append(f"- [{name}]({item.get('url', '#')}) ★{stars} - {desc}")
        lines.append("")

    # 数据开发
    data_focus = data.get("data_focus", [])
    if data_focus:
        lines.append("### 📊 数据开发相关")
        for item in data_focus[:3]:
            name = item.get("name", "")
            stars = item.get("stars", "")
            cn_trans = item.get("_cn_translate", "")
            desc = cn_trans or item.get("description", "")[:60]
            lines.append(f"- [{name}]({item.get('url', '#')}) ★{stars} - {desc}")
        lines.append("")

    # 安全通告
    advisories = data.get("advisories", [])
    if advisories:
        lines.append("### ⚠️ 安全通告")
        for item in advisories[:3]:
            severity = item.get("severity", "unknown")
            lines.append(f"- [{item.get('name', '')}]({item.get('url', '#')}) - 严重度 {severity}")
        lines.append("")

    # 版本发布
    releases = data.get("releases", [])
    if releases:
        lines.append("### 🚀 版本发布")
        for item in releases[:3]:
            lines.append(f"- [{item.get('name', '')}]({item.get('url', '#')})")
        lines.append("")

    # HN 热点
    hn_stories = data.get("hn_stories", [])
    if hn_stories:
        lines.append("### 📰 Hacker News 热点")
        for item in hn_stories[:3]:
            lines.append(f"- [{item.get('name', '')}]({item.get('url', '#')}) - {item.get('description', '')[:60]}")
        lines.append("")

    lines.append("---")
    lines.append("_完整日报请查看本地 HTML 文件_")

    return title, "\n".join(lines)


def send_to_wechat(sendkey, title, content):
    """发送消息到单个 SendKey"""
    url = SERVERCHAN_URL.format(key=sendkey)
    try:
        resp = requests.post(url, data={"title": title, "desp": content}, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 0:
                print(f"  ✅ 推送成功 (SendKey: {sendkey[:8]}...)")
                return True
            else:
                print(f"  ⚠️ 推送返回异常: {result.get('message', 'unknown')}")
                return False
        else:
            print(f"  ⚠️ 推送 HTTP {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  ❌ 推送失败: {e}")
        return False


def notify():
    """主入口：读取今日数据，推送到所有 SendKey"""
    config = load_config()
    sendkeys = [k.strip() for k in config.get("sendkeys", []) if k.strip()]
    # 过滤掉占位符
    sendkeys = [k for k in sendkeys if not k.startswith("请")]

    if not sendkeys:
        print("❌ 未配置有效的 SendKey，请先在 config.json 中填写")
        print("   获取方式: https://sct.ftqq.com 扫码注册")
        return 1

    # 读取今日数据
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    data_path = os.path.join(DATA_DIR, f"{today}.json")
    if not os.path.exists(data_path):
        files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".json")], reverse=True)
        if not files:
            print("❌ 没有找到数据文件，请先运行 collect.py")
            return 1
        data_path = os.path.join(DATA_DIR, files[0])
        print(f"⚠️ 未找到今日数据，使用最近的数据: {files[0]}")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title, content = build_message(data)
    print(f"📤 推送消息: {title}")
    print(f"   接收人数: {len(sendkeys)}")

    success = 0
    for sendkey in sendkeys:
        if send_to_wechat(sendkey, title, content):
            success += 1

    print(f"\n{'✅' if success else '❌'} 推送完成: {success}/{len(sendkeys)} 成功")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    sys.exit(notify())