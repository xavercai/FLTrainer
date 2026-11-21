#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日素材抓取：从德语新闻 RSS 里挑出 3–5 句适合跟读的句子，写成 news/daily.json。

给 GitHub Actions 定时跑（见 .github/workflows/daily.yml），也可以本地手动跑：
    python scripts/fetch_daily.py

只用 Python 标准库，不装任何依赖。
设计原则：宁可保留上一份，也不写一份空的 —— 全部源失败时以退出码 1 结束，
并保持已存在的 news/daily.json 不变，这样站点上永远有素材可用。
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

# ---- 源列表：与工具内置的 09-news.js 保持一致 ---------------------------------
FEEDS = [
    ("tagesschau", "Tagesschau（德国电视一台）", "https://www.tagesschau.de/xml/rss2", "生活"),
    ("dw",         "Deutsche Welle 德语新闻",     "https://rss.dw.com/rdf/rss-de-all",  "生活"),
    ("ams",        "auto motor und sport",        "https://www.auto-motor-und-sport.de/rss/news/", "汽车"),
    ("heiseA",     "heise Autos",                 "https://www.heise.de/themen/auto.rss",     "汽车"),
    ("spiegelA",   "SPIEGEL Auto",                "https://www.spiegel.de/auto/index.rss",    "汽车"),
    ("zeitA",      "ZEIT Mobilität",              "https://newsfeed.zeit.de/mobilitaet/index", "汽车"),
]

MAX_CARDS = 5            # 最多几条
PER_FEED = 2             # 每个源最多取几条
TZ = dt.timezone(dt.timedelta(hours=8))   # 中文用户时区，决定"今天是哪天"
UA = "Mozilla/5.0 (compatible; DeutschNewsCoach/1.0; +https://github.com/)"

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "news" / "daily.json"


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str, timeout: int = 20) -> str | None:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        if not raw:
            return None
        return raw.decode("utf-8", "replace")
    except Exception as exc:                      # noqa: BLE001 - 单源失败不应中断整体
        log(f"  × {url} -> {type(exc).__name__}: {exc}")
        return None


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def text_of(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]*>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_items(xml_text: str, feed_name: str, topic: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log(f"  × {feed_name}: XML 解析失败 {exc}")
        return []
    items = []
    for el in root.iter():
        if local_name(el.tag) not in ("item", "entry"):
            continue
        title = desc = link = date = ""
        for child in el:
            name = local_name(child.tag)
            if name == "title":
                title = text_of(child)
            elif name in ("description", "summary", "content"):
                if not desc:
                    desc = text_of(child)
            elif name == "link":
                link = (child.get("href") or text_of(child) or "").strip()
            elif name in ("pubdate", "updated", "date", "published"):
                if not date:
                    date = text_of(child)
        title = strip_html(title)
        desc = strip_html(desc)
        if title:
            items.append({"feed": feed_name, "topic": topic, "title": title,
                          "desc": desc, "link": link, "date": date})
    return items


def sentence_from(item: dict) -> str:
    """从标题/摘要里取一句适合跟读的德语。"""
    title = re.sub(r"^(dpa|afp|rtr|reuters|epd)[\s/\-]*", "", item["title"], flags=re.I).strip()
    if 18 <= len(title) <= 120:
        return title
    desc = re.sub(r"^(dpa|afp|rtr|reuters|epd)[\s/\-]*", "", item["desc"], flags=re.I).strip()
    m = re.search(r"[^.!?]{15,120}[.!?]", desc)
    if m:
        return m.group(0).strip()
    return (desc[:110] or title).strip()


def score(item: dict) -> float:
    s = 0.0
    n = len(item["title"])
    if 25 <= n <= 95:
        s += 40
    elif n < 120:
        s += 15
    if re.search(r"auto|elektro|laden|verkehr|motor|fahrzeug|suv", item["title"], re.I):
        s += 8
    return s


def norm(s: str) -> str:
    return re.sub(r"\W+", "", s.lower())


def main() -> int:
    day = dt.datetime.now(TZ).date().isoformat()
    log(f"=== 抓取 {day} 的德语新闻素材 ===")

    collected: list[dict] = []
    ok_feeds = 0
    for fid, name, url, topic in FEEDS:
        xml = fetch(url)
        if not xml:
            continue
        items = parse_items(xml, name, topic)
        if items:
            ok_feeds += 1
            log(f"  ✓ {name}: {len(items)} 条")
        collected.extend(items)

    if not collected:
        log("!! 所有源都失败，保留现有 daily.json 不动。")
        return 1

    collected.sort(key=score, reverse=True)

    picked: list[dict] = []
    per_feed: dict[str, int] = {}
    seen: set[str] = set()
    for it in collected:
        if per_feed.get(it["feed"], 0) >= PER_FEED:
            continue
        body = sentence_from(it)
        if len(body) < 12:
            continue
        k = norm(body)
        if k in seen:
            continue
        seen.add(k)
        per_feed[it["feed"]] = per_feed.get(it["feed"], 0) + 1
        picked.append({**it, "text": body})
        if len(picked) >= MAX_CARDS:
            break

    if not picked:
        log("!! 没挑出可用句子，保留现有 daily.json 不动。")
        return 1

    cards = [{
        "id": f"N-{day}-{i}",
        "topic": it["topic"],
        "source": it["feed"],
        "title": it["title"],
        "text": it["text"],
        "link": it["link"],
        "date": it["date"],
        "isNews": True,
    } for i, it in enumerate(picked)]

    payload = {
        "date": day,
        "generatedAt": int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000),
        "source": "live",
        "feedsOk": ok_feeds,
        "cards": cards,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"✓ 写入 {OUT}（{len(cards)} 条，{ok_feeds}/{len(FEEDS)} 个源可用）")
    for c in cards:
        log(f"    · [{c['topic']}] {c['text'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
