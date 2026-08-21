#!/usr/bin/env python3
"""GitHub Daily Digest - Data Collection Module
采集 GitHub Trending / 热门仓库 / 文章讨论 / 安全通告 / Hacker News 等数据
"""

import json
import os
import re
import sys
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ---------- 加载配置 ----------
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

FOCUS_AI = config["focus"]["ai"]
FOCUS_DATA = config["focus"]["data"]
WATCH_REPOS = config["watch_repos"]
GITHUB_TOKEN = config.get("github_token", "") or ""

# 信任系统证书 + 容错：本机可能存在自签名/缺失证书链的情况
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"
_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)


def match_keyword(description, topics):
    """检查 description 或 topics 是否匹配关注关键词"""
    text = (description or "").lower()
    for kw in FOCUS_AI + FOCUS_DATA:
        if kw in text:
            return True
    for t in (topics or []):
        if t.lower() in FOCUS_AI or t.lower() in FOCUS_DATA:
            return True
    return False


def http_get(url, timeout=15):
    """带 SSL 容错的 GET 请求（本机证书链可能缺失）"""
    try:
        return _SESSION.get(url, timeout=timeout)
    except requests.exceptions.SSLError:
        return _SESSION.get(url, timeout=timeout, verify=False)
    except requests.exceptions.ConnectionError:
        return _SESSION.get(url, timeout=timeout, verify=False)


def parse_stars(text):
    """解析 Trending 上的 Star 数字（如 '1.2k stars' → 1200）"""
    if isinstance(text, (int, float)):
        return int(text)
    text = (text or "").strip().lower().replace("stars", "").replace("star", "").strip()
    if "k" in text:
        try:
            return int(float(text.replace("k", "")) * 1000)
        except ValueError:
            return 0
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return 0


def is_chinese(text):
    """检测文本是否包含中文字符"""
    if not text:
        return False
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))


def translate_text(text, target_lang="zh-CN"):
    """使用 Google 免费翻译接口翻译英文文本到中文"""
    if not text or is_chinese(text):
        return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target_lang}&dt=t&q={urllib.parse.quote(text[:500])}"
        resp = http_get(url, timeout=8)
        if resp.status_code == 200:
            result = resp.json()
            if result and result[0]:
                translated = "".join(part[0] for part in result[0] if part[0])
                if translated:
                    return translated
        return text
    except Exception:
        return text


def get_hellogithub():
    """采集 HelloGitHub 中文热门项目推荐（RSS 期刊摘要）"""
    items = []
    try:
        resp = http_get("https://hellogithub.com/rss/", timeout=15)
        if resp.status_code != 200:
            return items
        root = ElementTree.fromstring(resp.content)
        for entry in root.findall(".//item")[:3]:
            title = entry.findtext("title", "")
            desc = entry.findtext("description", "")
            link = entry.findtext("link", "")
            items.append({
                "type": "chinese_picks",
                "name": title.strip(),
                "description": (desc or "").strip()[:200],
                "stars": 0,
                "topics": [],
                "url": link,
                "source": "hellogithub",
                "is_chinese": True
            })
    except Exception:
        pass
    return items


def search_chinese_repos(keywords, per_page=10):
    """搜索中文描述的热门仓库（混合中文关键词）"""
    items = []
    chinese_keywords = ["人工智能", "开源", "大模型", "数据", "AI", "机器学习"]
    seen = set()
    for kw in chinese_keywords:
        query = f"{kw} in:description"
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page=5"
        try:
            resp = http_get(url, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for repo in data.get("items", []):
                name = repo["full_name"]
                if name not in seen:
                    seen.add(name)
                    items.append({
                        "type": "chinese_picks",
                        "name": name,
                        "description": repo["description"] or "",
                        "stars": repo["stargazers_count"],
                        "topics": repo.get("topics", []),
                        "url": repo["html_url"],
                        "source": "chinese-picks",
                        "is_chinese": True
                    })
        except Exception:
            continue
    return items


def get_recommended_authors():
    """返回中文优质作者/周刊推荐列表（静态数据，定期更新）"""
    return [
        {
            "type": "author_recommend",
            "name": "HelloGitHub 月刊",
            "description": "每月 28 号分享 GitHub 上有趣、入门级的开源项目，涵盖 Python、Java、Go、前端、AI 等各个领域，每个项目都有中文介绍和截图，已持续发布 124 期。",
            "stars": 96300,
            "topics": ["开源项目", "月刊", "全领域", "入门友好"],
            "url": "https://github.com/521xueweihan/HelloGitHub",
            "source": "削微寒 (521xueweihan)",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "前端精读周刊",
            "description": "每周精读一篇国外优质技术文章，深度解读 React、TypeScript、设计模式、源码分析等内容，结合大厂经验做剖析，已出 296 期。",
            "stars": 31100,
            "topics": ["前端", "深度解读", "源码分析", "设计模式"],
            "url": "https://github.com/ascoders/weekly",
            "source": "黄子毅 (ascoders)",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "OpenGithub 精选开源项目周刊",
            "description": "每周一更新，精选 GitHub 上热门开源项目，涵盖 AI、ChatGPT、算法、工具等，持续更新 3 年+。",
            "stars": 1700,
            "topics": ["开源项目", "周刊", "全领域"],
            "url": "https://github.com/OpenGithubs/weekly",
            "source": "OpenGithubs 社区",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "前端食堂技术周刊",
            "description": "每周整理前端、全栈、AI 领域的技术资讯、文章、工具，定位轻量资讯汇总，已出 136 期。",
            "stars": 2100,
            "topics": ["前端", "全栈", "AI", "资讯汇总"],
            "url": "https://github.com/Geekhyt/weekly",
            "source": "童欧巴 (Geekhyt)",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "二丫讲梵的学习周刊",
            "description": "以运维技术和 Go 语言为主，兼收 GitHub 优秀项目，每周筛选优质内容汇总，已持续更新 276 期。",
            "stars": 607,
            "topics": ["运维", "Go 语言", "DevOps", "精选"],
            "url": "https://github.com/eryajf/learning-weekly",
            "source": "二丫讲梵 (eryajf)",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "Python 潮流周刊",
            "description": "精心筛选国内外最值得分享的 Python 文章、教程、开源项目、工具、播客和视频，帮助 Python 开发者保持技术敏感度。",
            "stars": 0,
            "topics": ["Python", "教程", "开源项目", "播客"],
            "url": "https://github.com/chinesehuazhou/python-weekly",
            "source": "豌豆花下猫 (chinesehuazhou)",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "老司机 iOS 周报",
            "description": "老司机技术团队维护的 iOS 开发者周报，覆盖 Swift、Xcode、Apple 生态最新动态，已出 200+ 期。",
            "stars": 0,
            "topics": ["iOS", "Swift", "Apple", "移动开发"],
            "url": "https://github.com/SwiftOldDriver/iOS-Weekly",
            "source": "老司机技术 (SwiftOldDriver)",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "独立开发变现周刊",
            "description": "关注独立开发者如何赚钱和变现，分享独立开发者的产品思路、运营经验和收入数据。",
            "stars": 0,
            "topics": ["独立开发", "变现", "产品", "创业"],
            "url": "https://github.com/weijunext/indie-maker-tools",
            "source": "社区维护",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "潮流周刊",
            "description": "前端 + 设计美学周刊，每期分享前端技术、设计案例和效率工具，视觉风格清新舒适。",
            "stars": 0,
            "topics": ["前端", "设计", "效率工具", "美学"],
            "url": "https://weekly.tw93.fun/",
            "source": "TW93",
            "is_chinese": True
        },
        {
            "type": "author_recommend",
            "name": "肖恩技术周刊",
            "description": "记录有价值的技术内容，对周内阅读的技术内容精品进行总结整理，保持技术敏感度。",
            "stars": 0,
            "topics": ["综合", "技术周刊", "精选"],
            "url": "https://github.com/Sean10/Sean10",
            "source": "肖恩 (Sean10)",
            "is_chinese": True
        },
    ]


def get_chinese_articles():
    """采集中文技术文章/周刊/博客"""
    items = []
    seen = set()

    # 1. 阮一峰科技爱好者周刊 - 爬取最新 Issue
    try:
        r = http_get("https://github.com/ruanyf/weekly/issues?q=is%3Aissue+is%3Aopen+sort%3Acreated-desc", timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("a[href*='/ruanyf/weekly/issues/']"):
                href = a.get("href", "")
                title = a.text.strip()
                if not title or "/issues/views" in href or "#issuecomment" in href:
                    continue
                issue_num = ""
                if "/issues/" in href:
                    issue_num = href.split("/issues/")[-1].split("/")[0]
                    if issue_num and issue_num.isdigit():
                        issue_num = f"#{issue_num}"
                url = f"https://github.com{href}" if href.startswith("/") else href
                if url not in seen:
                    seen.add(url)
                    items.append({
                        "type": "chinese_article",
                        "name": title.strip(),
                        "description": f"阮一峰科技爱好者周刊投稿 {issue_num}",
                        "stars": 0,
                        "topics": ["科技爱好者周刊", "中文"],
                        "url": url,
                        "source": "ruanyf-weekly",
                        "is_chinese": True
                    })
    except Exception as e:
        print(f"  [warn] ruanyf/weekly 抓取失败: {e}")

    # 2. ascoders/weekly - 前端精读周刊（爬 HTML）
    try:
        r = http_get("https://github.com/ascoders/weekly/issues?q=is%3Aissue+is%3Aopen+sort%3Acreated-desc", timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("a[href*='/ascoders/weekly/issues/']"):
                href = a.get("href", "")
                title = a.text.strip()
                if not title or "/issues/views" in href or "#issuecomment" in href:
                    continue
                url = f"https://github.com{href}" if href.startswith("/") else href
                if url not in seen:
                    seen.add(url)
                    items.append({
                        "type": "chinese_article",
                        "name": title.strip(),
                        "description": "前端精读周刊",
                        "stars": 0,
                        "topics": ["前端精读", "周刊", "中文"],
                        "url": url,
                        "source": "ascoders-weekly",
                        "is_chinese": True
                    })
    except Exception as e:
        print(f"  [warn] ascoders/weekly 抓取失败: {e}")

    # 3. OpenGithubs/weekly - 精选开源项目周刊（爬 HTML）
    try:
        r = http_get("https://github.com/OpenGithubs/weekly/issues?q=is%3Aissue+is%3Aopen+sort%3Acreated-desc", timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("a[href*='/OpenGithubs/weekly/issues/']"):
                href = a.get("href", "")
                title = a.text.strip()
                if not title or "/issues/views" in href or "#issuecomment" in href:
                    continue
                url = f"https://github.com{href}" if href.startswith("/") else href
                if url not in seen:
                    seen.add(url)
                    items.append({
                        "type": "chinese_article",
                        "name": title.strip(),
                        "description": "OpenGithub 精选开源项目周刊",
                        "stars": 0,
                        "topics": ["OpenGithub", "周刊", "中文"],
                        "url": url,
                        "source": "opengithub-weekly",
                        "is_chinese": True
                    })
    except Exception as e:
        print(f"  [warn] OpenGithubs/weekly 抓取失败: {e}")

    return items[:20]  # 最多返回 20 条


def get_chinese_resources():
    """采集中文资源合集/书单/awesome 列表"""
    items = []
    seen = set()

    # 中文 awesome 合集 / 书单仓库
    resource_keywords = [
        ("awesome-programming-books", "经典编程书籍大全"),
        ("awesome-java-books", "Java 技术书籍大全"),
        ("free-programming-books", "免费编程书籍"),
        ("awesome-cs-books", "计算机书籍"),
    ]
    for repo_name, label in resource_keywords:
        try:
            url = f"https://api.github.com/search/repositories?q={repo_name}+in:name&sort=stars&order=desc&per_page=3"
            r = http_get(url, timeout=15)
            if r.status_code == 200:
                for repo in r.json().get("items", []):
                    name = repo["full_name"]
                    if name not in seen:
                        seen.add(name)
                        items.append({
                            "type": "chinese_resource",
                            "name": name,
                            "description": (repo.get("description") or label)[:200],
                            "stars": repo["stargazers_count"],
                            "topics": repo.get("topics", [])[:5],
                            "url": repo["html_url"],
                            "source": "chinese-resource",
                            "is_chinese": True
                        })
        except Exception:
            continue

    # 中文 awesome 集合（搜索中文描述的高星 awesome 仓库）
    try:
        r = http_get("https://api.github.com/search/repositories?q=awesome+in:name+description:中文&sort=stars&order=desc&per_page=10", timeout=15)
        if r.status_code == 200:
            for repo in r.json().get("items", []):
                name = repo["full_name"]
                desc = repo.get("description", "")
                if name not in seen and is_chinese(desc):
                    seen.add(name)
                    items.append({
                        "type": "chinese_resource",
                        "name": name,
                        "description": (desc or "中文资源合集")[:200],
                        "stars": repo["stargazers_count"],
                        "topics": repo.get("topics", [])[:5],
                        "url": repo["html_url"],
                        "source": "chinese-resource",
                        "is_chinese": True
                    })
    except Exception:
        pass

    return items[:10]


def get_trending():
    """采集 GitHub Trending 热榜"""
    items = []
    for lang in ["", "python", "javascript", "typescript", "go", "rust"]:
        url = "https://github.com/trending"
        if lang:
            url += f"/{lang}"
        url += "?since=daily"
        try:
            resp = http_get(url, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select("article.Box-row")
            for article in articles:
                h2 = article.select_one("h2 a")
                if not h2:
                    continue
                full_name = h2.get_text(strip=True).replace(" ", "")
                desc_el = article.select_one("p")
                desc = desc_el.get_text(strip=True) if desc_el else ""
                star_el = article.select_one("span.d-inline-block.float-sm-right")
                stars = star_el.get_text(strip=True) if star_el else ""
                # 提取 topic 标签
                topics = [t.get_text(strip=True) for t in article.select("a.topic-tag")]
                items.append({
                    "type": "trending",
                    "name": full_name,
                    "description": desc,
                    "stars": parse_stars(stars),
                    "topics": topics,
                    "url": f"https://github.com/{full_name}",
                    "source": "github-trending",
                    "is_chinese": is_chinese(desc) or is_chinese(full_name)
                })
        except Exception as e:
            print(f"  [warn] Trending({lang}) 抓取失败: {e}")
    return items


def search_github_repos(keywords, sort="stars", order="desc", per_page=15):
    """通过 GitHub Search API 搜索热门仓库（API 限制最多 5 个 OR 操作符，分批查询）"""
    items = []
    seen = set()
    # 每批最多 5 个关键词
    batch_size = 5
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i+batch_size]
        query = " OR ".join(batch)
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort={sort}&order={order}&per_page={per_page}"
        try:
            resp = http_get(url, timeout=15)
            if resp.status_code == 403:
                print("  [warn] GitHub API 限流，跳过 Search API")
                return items
            if resp.status_code != 200:
                print(f"  [warn] GitHub API 返回 {resp.status_code} {resp.text[:100]}")
                continue
            data = resp.json()
            for repo in data.get("items", []):
                name = repo["full_name"]
                if name not in seen:
                    seen.add(name)
                    items.append({
                        "type": "repo",
                        "name": name,
                        "description": repo["description"] or "",
                        "stars": repo["stargazers_count"],
                        "topics": repo.get("topics", []),
                        "url": repo["html_url"],
                        "source": "github-search",
                        "is_chinese": is_chinese(repo.get("description", "")) or is_chinese(name)
                    })
        except Exception as e:
            print(f"  [warn] GitHub Search 批次失败: {e}")
    return items


def search_github_issues(keywords, per_page=10):
    """搜索热门 Issue / Discussion 讨论（分批查询）"""
    items = []
    seen = set()
    batch_size = 5
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i+batch_size]
        query = " OR ".join(batch) + " is:issue is:open"
        url = f"https://api.github.com/search/issues?q={urllib.parse.quote(query)}&sort=reactions&order=desc&per_page={per_page}"
        try:
            resp = http_get(url, timeout=15)
            if resp.status_code == 403:
                return items
            if resp.status_code != 200:
                continue
            data = resp.json()
            for issue in data.get("items", []):
                url_i = issue["html_url"]
                if url_i not in seen:
                    seen.add(url_i)
                    items.append({
                        "type": "discussion",
                        "name": issue["title"],
                        "description": issue.get("body", "")[:200] if issue.get("body") else "",
                        "stars": issue.get("reactions", {}).get("total_count", 0),
                        "url": url_i,
                        "repo": issue["repository_url"].split("/")[-1] if "/" in issue["repository_url"] else "",
                        "source": "github-discussion",
                        "is_chinese": is_chinese(issue["title"]) or is_chinese(issue.get("body", ""))
                    })
        except Exception as e:
            print(f"  [warn] GitHub Issues 批次失败: {e}")
    return items


def get_github_advisories():
    """采集 GitHub 安全通告"""
    items = []
    url = "https://api.github.com/advisories?per_page=10&type=reviewed"
    try:
        resp = http_get(url, timeout=15)
        if resp.status_code == 403:
            return items
        if resp.status_code != 200:
            return items
        data = resp.json()
        for adv in data:
            items.append({
                "type": "advisory",
                "name": adv.get("summary", ""),
                "description": adv.get("description", "")[:200] if adv.get("description") else "",
                "severity": adv.get("severity", "unknown"),
                "url": adv.get("html_url", ""),
                "source": "github-advisory",
                "is_chinese": is_chinese(adv.get("summary", ""))
            })
    except Exception as e:
        print(f"  [warn] Advisory 获取失败: {e}")
    return items


def get_hacker_news():
    """采集 Hacker News 高分帖（只取前 15 个故事，避免过多请求）"""
    items = []
    try:
        resp = http_get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        if resp.status_code != 200:
            return items
        ids = resp.json()[:10]
        for story_id in ids:
            try:
                sr = http_get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=8)
                if sr.status_code != 200:
                    continue
                story = sr.json()
                if not story or not story.get("title"):
                    continue
                # 只保留 GitHub 相关或高分帖
                score = story.get("score", 0)
                title = story.get("title", "")
                url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                is_github = "github" in (title + url).lower()
                if is_github or score >= 50:
                    items.append({
                        "type": "hn-story",
                        "name": title,
                        "description": f"Score: {score} | by {story.get('by', 'unknown')}",
                        "stars": score,
                        "url": url,
                        "source": "hacker-news",
                        "is_chinese": is_chinese(title)
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"  [warn] Hacker News 获取失败: {e}")
    return items


def get_github_blog():
    """采集 GitHub Blog 最新动态"""
    items = []
    try:
        resp = http_get("https://github.blog/feed/", timeout=15)
        if resp.status_code != 200:
            # 尝试 changelog
            resp = http_get("https://github.blog/changelog/feed/", timeout=15)
        if resp.status_code != 200:
            return items
        root = ElementTree.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns) or root.findall("entry", ns)
        for entry in entries[:8]:
            title = entry.findtext("title", "") or entry.findtext("atom:title", "", ns)
            link = entry.find("link")
            url = ""
            if link is not None:
                url = link.get("href", "")
            summary = entry.findtext("summary", "") or entry.findtext("atom:summary", "", ns)
            items.append({
                "type": "blog",
                "name": title.strip() if title else "",
                "description": (summary or "").strip()[:200],
                "stars": 0,
                "url": url,
                "source": "github-blog",
                "is_chinese": is_chinese(title)
            })
    except Exception as e:
        print(f"  [warn] GitHub Blog 获取失败: {e}")
    return items


def get_releases():
    """采集关注仓库的近期 Release"""
    items = []
    for repo in WATCH_REPOS:
        try:
            url = f"https://api.github.com/repos/{repo}/releases?per_page=3"
            resp = http_get(url, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for rel in data:
                if not rel.get("tag_name"):
                    continue
                items.append({
                    "type": "release",
                    "name": f"{repo} {rel.get('tag_name', '')}",
                    "description": (rel.get("body", "") or "")[:200],
                    "stars": 0,
                    "url": rel.get("html_url", f"https://github.com/{repo}/releases"),
                    "source": "github-release",
                    "is_chinese": is_chinese(rel.get("body", ""))
                })
        except Exception as e:
            print(f"  [warn] Release 获取失败 ({repo}): {e}")
    return items


def filter_by_focus(items):
    """按 AI/数据 关键词筛选项目"""
    ai_items = []
    data_items = []
    other_items = []
    for item in items:
        desc = (item.get("description") or "").lower()
        name = (item.get("name") or "").lower()
        topics = [t.lower() for t in item.get("topics", [])]
        text = desc + " " + name + " " + " ".join(topics)
        is_ai = any(kw in text for kw in FOCUS_AI)
        is_data = any(kw in text for kw in FOCUS_DATA)
        if is_ai:
            ai_items.append(item)
        elif is_data:
            data_items.append(item)
        else:
            other_items.append(item)
    return ai_items, data_items, other_items


def sort_by_chinese(items):
    """中文优先排序：中文项目在前，英文在后"""
    cn = [i for i in items if i.get("is_chinese")]
    en = [i for i in items if not i.get("is_chinese")]
    return cn + en


def translate_item(item):
    """为英文项目添加中文翻译"""
    desc = item.get("description", "")
    name = item.get("name", "")
    if not item.get("is_chinese"):
        if desc and not is_chinese(desc):
            item["_cn_translate"] = translate_text(desc[:200])
        if name and not is_chinese(name):
            item["_cn_name"] = translate_text(name.split("/")[-1] if "/" in name else name)
    return item


def collect():
    print("=" * 50)
    print("GitHub Digest - 数据采集")
    print(f"时间: {datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 1. Trending + 中文推荐 + 作者推荐
    print("\n[1/6] 采集 GitHub Trending + 中文推荐 ...")
    trending = get_trending()
    hellogithub = get_hellogithub()
    chinese_picks = search_chinese_repos(None)
    chinese_articles = get_chinese_articles()
    chinese_resources = get_chinese_resources()
    author_recommends = get_recommended_authors()
    print(f"  Trending: {len(trending)} 条 | HelloGitHub: {len(hellogithub)} 条 | 中文项目: {len(chinese_picks)} 条 | 中文文章: {len(chinese_articles)} 条 | 资源合集: {len(chinese_resources)} 条 | 作者推荐: {len(author_recommends)} 位")

    # 2. GitHub Search - AI 相关
    print("\n[2/6] 搜索 AI 相关热门仓库 ...")
    ai_repos = search_github_repos(FOCUS_AI, per_page=10)
    print(f"  获取到 {len(ai_repos)} 条 AI 仓库")

    # 3. GitHub Search - 数据开发相关
    print("\n[3/6] 搜索数据开发相关热门仓库 ...")
    data_repos = search_github_repos(FOCUS_DATA, per_page=10)
    print(f"  获取到 {len(data_repos)} 条数据仓库")

    # 4. 热门讨论 / Issue
    print("\n[4/6] 搜索热门讨论 ...")
    discussions = search_github_issues(FOCUS_AI + FOCUS_DATA, per_page=10)
    print(f"  获取到 {len(discussions)} 条讨论")

    # 5. 安全通告 + HN + Blog
    print("\n[5/6] 采集安全通告 / Hacker News / GitHub Blog ...")
    advisories = get_github_advisories()[:5]
    hn = get_hacker_news()
    blog = get_github_blog()[:5]
    print(f"  安全通告: {len(advisories)} | HN: {len(hn)} | Blog: {len(blog)}")

    # 6. 版本发布
    print("\n[6/6] 采集版本发布 ...")
    releases = get_releases()
    print(f"  获取到 {len(releases)} 条发布")

    # 合并所有数据
    all_items = trending + hellogithub + chinese_picks + chinese_articles + chinese_resources + author_recommends + ai_repos + data_repos + discussions + advisories + hn + blog + releases

    # 去重（按 url 去重）
    seen = set()
    unique_items = []
    for item in all_items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique_items.append(item)

    # 翻译英文内容（最多翻译前 50 条，避免过多请求）
    print(f"\n  🌐 翻译英文内容...")
    import time as _time
    translated_count = 0
    for item in unique_items[:50]:
        if not item.get("is_chinese"):
            translate_item(item)
            translated_count += 1
            _time.sleep(0.3)  # 避免 Google 翻译限流
    print(f"  翻译了 {translated_count} 条英文内容")

    # 按 focus 分类
    ai_items, data_items, other_items = filter_by_focus(unique_items)

    # 按 type 分组
    by_type = {}
    for item in unique_items:
        t = item["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(item)

    # 构建输出
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    output = {
        "date": today,
        "total": len(unique_items),
        "summary": {
            "ai_related": len(ai_items),
            "data_related": len(data_items),
            "other": len(other_items)
        },
        "by_category": {
            "trending": len(by_type.get("trending", [])),
            "repos": len(by_type.get("repo", [])),
            "discussions": len(by_type.get("discussion", [])),
            "advisories": len(by_type.get("advisory", [])),
            "hn_stories": len(by_type.get("hn-story", [])),
            "blog_posts": len(by_type.get("blog", [])),
            "releases": len(by_type.get("release", [])),
            "chinese_articles": len(by_type.get("chinese_article", [])),
            "chinese_resources": len(by_type.get("chinese_resource", [])),
            "author_recommends": len(by_type.get("author_recommend", []))
        },
        "ai_focus": ai_items[:10],
        "data_focus": data_items[:10],
        "chinese_picks": chinese_picks[:10],
        "chinese_articles": chinese_articles[:10],
        "chinese_resources": chinese_resources[:10],
        "author_recommends": author_recommends,
        "trending": trending[:10],
        "discussions": discussions[:10],
        "advisories": advisories[:10],
        "hn_stories": hn[:10],
        "blog_posts": blog[:10],
        "releases": releases[:10],
        "other": other_items[:10]
    }

    # 写文件
    filepath = os.path.join(DATA_DIR, f"{today}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已保存: {filepath}")
    print(f"   总计 {output['total']} 条 | AI: {output['summary']['ai_related']} | 数据: {output['summary']['data_related']}")

    return output


if __name__ == "__main__":
    collect()