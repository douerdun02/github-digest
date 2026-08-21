#!/usr/bin/env python3
"""GitHub Daily Digest - HTML Generation Module
读取 JSON 数据，生成卡片式 HTML 日报
"""

import json
import os
import shutil
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

os.makedirs(DOCS_DIR, exist_ok=True)

CATEGORY_NAMES = {
    "chinese_picks": "🇨🇳 中文热门项目",
    "chinese_articles": "📝 中文文章动态",
    "chinese_resources": "📚 资源合集推荐",
    "author_recommends": "👤 中文作者推荐",
    "trending": "Trending 热榜",
    "ai_focus": "AI 相关项目",
    "data_focus": "数据开发相关",
    "discussions": "热门讨论",
    "advisories": "安全通告",
    "hn_stories": "Hacker News 热点",
    "blog_posts": "GitHub 官方动态",
    "releases": "版本发布"
}

CATEGORY_ICONS = {
    "chinese_picks": "🇨🇳",
    "chinese_articles": "📝",
    "chinese_resources": "📚",
    "author_recommends": "👤",
    "trending": "🔥",
    "ai_focus": "🤖",
    "data_focus": "📊",
    "discussions": "💬",
    "advisories": "⚠️",
    "hn_stories": "📰",
    "blog_posts": "📝",
    "releases": "🚀"
}

CATEGORY_ORDER = [
    "chinese_articles", "chinese_picks", "chinese_resources", "author_recommends", "trending", "ai_focus", "data_focus", "discussions",
    "advisories", "hn_stories", "blog_posts", "releases"
]


def render_card(item, show_topics=True):
    """渲染单个卡片 HTML"""
    name = item.get("name", "Unknown")
    cn_name = item.get("_cn_name", "")
    desc = item.get("description", "")
    cn_translate = item.get("_cn_translate", "")
    url = item.get("url", "#")
    stars = item.get("stars", 0)
    source = item.get("source", "")
    topics = item.get("topics", [])

    # 格式化 stars
    if isinstance(stars, (int, float)):
        if stars >= 1000:
            stars_text = f"{stars/1000:.1f}k"
        else:
            stars_text = str(stars)
    else:
        stars_text = str(stars)

    # 中文翻译行
    cn_translate_html = ""
    if cn_translate:
        cn_translate_html = f'<p class="card-cn">📖 {cn_translate}</p>'
    elif cn_name:
        cn_translate_html = f'<p class="card-cn">📖 {cn_name}</p>'

    # 话题标签
    tags_html = ""
    if show_topics and topics:
        tags = "".join(f'<span class="tag">{t}</span>' for t in topics[:5])
        tags_html = f'<div class="tags">{tags}</div>'

    # 生成唯一标识用于收藏
    item_id = url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_")[:80]

    return f"""
    <div class="card">
      <button class="star-btn" data-id="{item_id}" data-name="{name.replace('"', '&quot;')}" data-url="{url}" data-desc="{(desc[:100] if desc else '').replace('"', '&quot;')}" onclick="event.preventDefault(); toggleStar(this)" title="点击收藏">☆</button>
      <a href="{url}" target="_blank" class="card-link">
        <div class="card-header">
          <span class="card-name">{name}</span>
          <span class="card-stars">★ {stars_text}</span>
        </div>
        <div class="card-body">
          <p class="card-desc">{desc[:200] if desc else "暂无描述"}</p>
          {cn_translate_html}
          {tags_html}
        </div>
        <div class="card-footer">
          <span class="card-source">{source}</span>
        </div>
      </a>
    </div>
    """


def render_author_card(item):
    """渲染作者推荐卡片（与普通卡片不同，更强调作者信息）"""
    name = item.get("name", "Unknown")
    desc = item.get("description", "")
    url = item.get("url", "#")
    stars = item.get("stars", 0)
    source = item.get("source", "")
    topics = item.get("topics", [])

    # 格式化 stars
    if isinstance(stars, (int, float)):
        if stars >= 1000:
            stars_text = f"{stars/1000:.1f}k"
        else:
            stars_text = str(stars) if stars > 0 else ""
    else:
        stars_text = str(stars) if stars else ""

    # 话题标签
    tags_html = ""
    if topics:
        tags = "".join(f'<span class="tag tag-author">{t}</span>' for t in topics[:5])
        tags_html = f'<div class="tags">{tags}</div>'

    stars_html = f'<span class="author-stars">★ {stars_text}</span>' if stars_text else ""

    return f"""
    <div class="author-card">
      <a href="{url}" target="_blank" class="author-card-link">
        <div class="author-card-top">
          <div class="author-avatar">{name[0]}</div>
          <div class="author-meta">
            <span class="author-name">{name}</span>
            <span class="author-source">👤 {source}</span>
          </div>
          {stars_html}
        </div>
        <div class="author-card-body">
          <p class="author-desc">{desc[:300]}</p>
          {tags_html}
        </div>
      </a>
    </div>
    """


def render_section(section_id, items, max_items=10):
    """渲染一个板块"""
    if not items:
        return ""

    title = CATEGORY_NAMES.get(section_id, section_id)
    icon = CATEGORY_ICONS.get(section_id, "📌")

    if section_id == "author_recommends":
        # 作者推荐使用特殊卡片排版
        cards_html = "".join(render_author_card(item) for item in items[:max_items])
        return f"""
        <section id="{section_id}" class="section">
          <h2 class="section-title">{icon} {title} <span class="count">{len(items[:max_items])}</span></h2>
          <div class="author-grid">
            {cards_html}
          </div>
        </section>
        """

    # 中文优先排序
    sorted_items = sorted(items[:max_items], key=lambda x: (0 if x.get("is_chinese") else 1, -(x.get("stars", 0) or 0)))
    cards_html = "".join(render_card(item) for item in sorted_items[:max_items])

    return f"""
    <section id="{section_id}" class="section">
      <h2 class="section-title">{icon} {title} <span class="count">{len(items[:max_items])}</span></h2>
      <div class="card-grid">
        {cards_html}
      </div>
    </section>
    """


def build_html(data):
    """生成完整 HTML 日报"""
    today = data.get("date", datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"))
    summary = data.get("summary", {})
    by_category = data.get("by_category", {})

    # 构建导航栏
    nav_items = ""
    sections_html = ""
    for cat in CATEGORY_ORDER:
        items = data.get(cat, [])
        if items:
            icon = CATEGORY_ICONS.get(cat, "📌")
            name = CATEGORY_NAMES.get(cat, cat)
            nav_items += f'<a href="#{cat}" class="nav-link">{icon} {name}</a>'
            sections_html += render_section(cat, items)

    # 如果没有任何数据，显示提示
    if not sections_html:
        sections_html = '<div class="empty-state">暂无数据，请稍后再来查看</div>'

    # 统计信息
    ai_count = summary.get("ai_related", 0)
    data_count = summary.get("data_related", 0)
    total_count = data.get("total", 0)

    # 构建完整 HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GitHub 摘要大全 - {today}</title>
<style>
  :root {{
    --bg: #0d1117;
    --bg-card: #161b22;
    --bg-card-hover: #1c2333;
    --bg-nav: #0d1117e0;
    --border: #30363d;
    --text: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --accent: #58a6ff;
    --accent-green: #3fb950;
    --accent-yellow: #d29922;
    --accent-orange: #d9863b;
    --accent-red: #f85149;
    --accent-purple: #bc8cff;
    --radius: 8px;
    --radius-lg: 12px;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
  }}
  .header {{
    border-bottom: 1px solid var(--border);
    padding: 24px 20px 16px;
    text-align: center;
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--bg);
  }}
  .header h1 {{
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 4px;
  }}
  .header .date {{
    font-size: 14px;
    color: var(--text-secondary);
  }}
  .nav {{
    display: flex;
    gap: 8px;
    padding: 12px 20px;
    overflow-x: auto;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 80px;
    z-index: 99;
    background: var(--bg-nav);
    backdrop-filter: blur(8px);
    -webkit-overflow-scrolling: touch;
  }}
  .nav-link {{
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 13px;
    padding: 6px 12px;
    border-radius: var(--radius);
    white-space: nowrap;
    transition: all 0.2s;
    flex-shrink: 0;
  }}
  .nav-link:hover {{
    color: var(--text);
    background: var(--bg-card);
  }}
  .stats-bar {{
    display: flex;
    gap: 12px;
    padding: 16px 20px;
    justify-content: center;
    flex-wrap: wrap;
  }}
  .stat {{
    text-align: center;
    padding: 12px 20px;
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    border: 1px solid var(--border);
    min-width: 100px;
  }}
  .stat-number {{
    font-size: 24px;
    font-weight: 600;
    color: var(--accent);
  }}
  .stat-label {{
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
  }}
  .main {{
    max-width: 960px;
    margin: 0 auto;
    padding: 20px;
  }}
  .section {{
    margin-bottom: 32px;
  }}
  .section-title {{
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .section-title .count {{
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--bg-card);
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 400;
  }}
  .card-grid {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
  }}
  @media (min-width: 640px) {{
    .card-grid {{ grid-template-columns: 1fr 1fr; }}
  }}
  .card {{
    position: relative;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    transition: all 0.2s;
    overflow: hidden;
  }}
  .card:hover {{
    background: var(--bg-card-hover);
    border-color: var(--accent);
  }}
  .card-link {{
    display: block;
    padding: 14px 16px;
    text-decoration: none;
    color: inherit;
  }}
  .card-link:hover {{
    transform: translateY(-1px);
  }}
  .star-btn {{
    position: absolute;
    top: 4px;
    right: 4px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: none;
    background: rgba(0,0,0,0.3);
    color: var(--text-muted);
    font-size: 15px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    z-index: 10;
    line-height: 1;
  }}
  .star-btn:hover {{
    background: rgba(210, 153, 34, 0.3);
    color: var(--accent-yellow);
    transform: scale(1.2);
  }}
  .star-btn.starred {{
    color: var(--accent-yellow);
    background: rgba(210, 153, 34, 0.25);
  }}
  .card {{
    display: block;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    text-decoration: none;
    color: inherit;
    transition: all 0.2s;
  }}
  .card:hover {{
    background: var(--bg-card-hover);
    border-color: var(--accent);
    transform: translateY(-1px);
  }}
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 6px;
    gap: 8px;
  }}
  .card-name {{
    font-size: 14px;
    font-weight: 600;
    color: var(--accent);
    word-break: break-all;
  }}
  .card-stars {{
    font-size: 12px;
    color: var(--accent-yellow);
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .card-body {{
    margin-bottom: 6px;
  }}
  .card-desc {{
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .card-cn {{
    font-size: 12px;
    color: var(--accent-green);
    margin-top: 4px;
    line-height: 1.4;
  }}
  .tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;
  }}
  .tag {{
    font-size: 11px;
    color: var(--accent);
    background: rgba(88, 166, 255, 0.1);
    padding: 2px 8px;
    border-radius: 12px;
    border: 1px solid rgba(88, 166, 255, 0.2);
  }}
  .card-footer {{
    font-size: 11px;
    color: var(--text-muted);
  }}
  .card-source {{
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  /* 作者推荐卡片 */
  .author-grid {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
  }}
  @media (min-width: 640px) {{
    .author-grid {{ grid-template-columns: 1fr 1fr; }}
  }}
  .author-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    transition: all 0.2s;
    overflow: hidden;
  }}
  .author-card:hover {{
    background: var(--bg-card-hover);
    border-color: var(--accent-purple);
    transform: translateY(-2px);
  }}
  .author-card-link {{
    display: block;
    padding: 16px;
    text-decoration: none;
    color: inherit;
  }}
  .author-card-top {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
  }}
  .author-avatar {{
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--accent-purple), var(--accent));
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 700;
    flex-shrink: 0;
  }}
  .author-meta {{
    flex: 1;
    min-width: 0;
  }}
  .author-name {{
    font-size: 14px;
    font-weight: 600;
    color: var(--accent);
    display: block;
  }}
  .author-source {{
    font-size: 12px;
    color: var(--text-secondary);
    display: block;
    margin-top: 2px;
  }}
  .author-stars {{
    font-size: 13px;
    color: var(--accent-yellow);
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .author-card-body {{
    padding-left: 0;
  }}
  .author-desc {{
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
  }}
  .tag-author {{
    color: var(--accent-purple);
    background: rgba(188, 140, 255, 0.1);
    border-color: rgba(188, 140, 255, 0.2);
  }}

  .empty-state {{
    text-align: center;
    padding: 40px;
    color: var(--text-muted);
  }}
  .footer {{
    text-align: center;
    padding: 24px;
    color: var(--text-muted);
    font-size: 12px;
    border-top: 1px solid var(--border);
  }}
  .footer a {{
    color: var(--accent);
    text-decoration: none;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>GitHub 摘要大全</h1>
    <div class="date">📅 {today} · 共收录 {total_count} 条内容</div>
  </div>

  <div class="nav">
    <a href="#favorites" class="nav-link" style="color:var(--accent-yellow);font-weight:600;">⭐ 收藏夹</a>
    {nav_items}
  </div>

  <div class="stats-bar">
    <div class="stat">
      <div class="stat-number">{total_count}</div>
      <div class="stat-label">总收录</div>
    </div>
    <div class="stat">
      <div class="stat-number">{ai_count}</div>
      <div class="stat-label">AI 相关</div>
    </div>
    <div class="stat">
      <div class="stat-number">{data_count}</div>
      <div class="stat-label">数据开发</div>
    </div>
    <div class="stat">
      <div class="stat-number">{by_category.get('trending', 0)}</div>
      <div class="stat-label">热榜</div>
    </div>
    <div class="stat">
      <div class="stat-number">{by_category.get('advisories', 0)}</div>
      <div class="stat-label">安全通告</div>
    </div>
  </div>

  <div class="main">
    <section id="favorites" class="section" style="display:none;">
      <h2 class="section-title">⭐ 我的收藏夹 <span class="count" id="fav-count">0</span></h2>
      <div id="favorites-list" class="card-grid">
        <div class="empty-state">还没有收藏内容，点击卡片旁的 ☆ 按钮即可收藏</div>
      </div>
    </section>
    {sections_html}
  </div>

  <div class="footer">
    <p>由 WorkBuddy 自动生成 · 每天 10:00 更新</p>
    <p><a href="https://sct.ftqq.com" target="_blank">微信推送由 Server酱 提供</a></p>
  </div>
</body>
<script>
const STORAGE_KEY = 'github_digest_favorites';
function getFavorites() {{
  try {{
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  }} catch(e) {{
    return [];
  }}
}}
function saveFavorites(favs) {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(favs));
}}
function toggleStar(btn) {{
  const id = btn.dataset.id;
  const favs = getFavorites();
  const idx = favs.findIndex(f => f.id === id);
  if (idx >= 0) {{
    favs.splice(idx, 1);
    btn.classList.remove('starred');
    btn.textContent = '☆';
  }} else {{
    favs.push({{
      id: id,
      name: btn.dataset.name,
      url: btn.dataset.url,
      desc: btn.dataset.desc,
      time: new Date().toISOString()
    }});
    btn.classList.add('starred');
    btn.textContent = '★';
  }}
  saveFavorites(favs);
  renderFavorites();
}}
function renderFavorites() {{
  const favs = getFavorites();
  const list = document.getElementById('favorites-list');
  const count = document.getElementById('fav-count');
  const section = document.getElementById('favorites');
  if (count) count.textContent = favs.length;
  if (favs.length === 0) {{
    if (list) list.innerHTML = '<div class="empty-state">还没有收藏内容，点击卡片旁的 ☆ 按钮即可收藏</div>';
    return;
  }}
  if (list) {{
    list.innerHTML = favs.map(f => `
      <div class="card">
        <button class="star-btn starred" data-id="${{f.id}}" onclick="removeFav('${{f.id}}')" title="取消收藏">★</button>
        <a href="${{f.url}}" target="_blank" class="card-link">
          <div class="card-header">
            <span class="card-name">${{f.name}}</span>
          </div>
          <div class="card-body">
            <p class="card-desc">${{f.desc || '暂无描述'}}</p>
          </div>
          <div class="card-footer">
            <span class="card-source">收藏于 ${{new Date(f.time).toLocaleDateString('zh-CN')}}</span>
          </div>
        </a>
      </div>
    `).join('');
  }}
}}
function removeFav(id) {{
  const favs = getFavorites().filter(f => f.id !== id);
  saveFavorites(favs);
  renderFavorites();
  document.querySelectorAll('.star-btn[data-id="' + id + '"]').forEach(b => {{
    b.classList.remove('starred');
    b.textContent = '☆';
  }});
}}
window.addEventListener('DOMContentLoaded', function() {{
  const favs = getFavorites();
  const favIds = new Set(favs.map(f => f.id));
  document.querySelectorAll('.star-btn').forEach(btn => {{
    if (favIds.has(btn.dataset.id)) {{
      btn.classList.add('starred');
      btn.textContent = '★';
    }}
  }});
  const favLink = document.querySelector('a[href="#favorites"]');
  if (favLink) {{
    favLink.addEventListener('click', function(e) {{
      e.preventDefault();
      const section = document.getElementById('favorites');
      if (section.style.display === 'none') {{
        section.style.display = 'block';
        renderFavorites();
        section.scrollIntoView({{ behavior: 'smooth' }});
      }} else {{
        section.style.display = 'none';
      }}
    }});
  }}
}});
</script>
</html>"""
    return html


def build():
    # 读取今日数据
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    data_path = os.path.join(DATA_DIR, f"{today}.json")

    if not os.path.exists(data_path):
        # 尝试找最近的数据
        files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".json")], reverse=True)
        if not files:
            print("❌ 没有找到数据文件，请先运行 collect.py")
            return
        data_path = os.path.join(DATA_DIR, files[0])
        today = files[0].replace(".json", "")
        print(f"⚠️ 未找到今日数据，使用最近的数据: {files[0]}")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📄 生成 HTML 日报: {data.get('date', today)}")
    html = build_html(data)

    # 写入历史存档
    archive_path = os.path.join(DOCS_DIR, f"github-digest-{today}.html")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ 历史存档: {archive_path}")

    # 复制为 index.html
    index_path = os.path.join(DOCS_DIR, "index.html")
    shutil.copy2(archive_path, index_path)
    print(f"  ✅ 最新版: {index_path}")

    return archive_path


if __name__ == "__main__":
    build()