import urllib.request
import xml.etree.ElementTree as ET
import re
import json
import io
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Channel list \u2014 uses RSSHub proxy (rsshub.rssforever.com) as primary feed source
# because YouTube blocks direct RSS requests from GitHub Actions IP ranges.
# Falls back to native YouTube RSS if the proxy is unavailable.
RSSHUB_BASE = "https://rsshub.rssforever.com/youtube/channel/"
YT_RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id="

# Only YouTube video URLs are trusted. Anything else from the feed
# (RSSHub proxy is third-party infrastructure) is dropped — defense in
# depth against a compromised or malicious feed source injecting
# arbitrary/javascript: URLs into videos.json and the rendered page.
VIDEO_ID_RE = re.compile(r"^[\w-]{6,20}$")

def safe_video_url(url):
    """Canonicalize to https://www.youtube.com/watch?v=<id> or drop.

    Rebuilds the URL from validated components so nothing from the raw
    feed value (query junk, attribute-breakout characters) survives.
    """
    from urllib.parse import urlparse, parse_qs
    if not url:
        return ""
    try:
        p = urlparse(url)
    except Exception:
        return ""
    if p.scheme != "https":
        return ""
    host = p.netloc.lower()
    vid = ""
    if host in ("www.youtube.com", "youtube.com") and p.path == "/watch":
        vid = (parse_qs(p.query).get("v") or [""])[0]
    elif host == "youtu.be":
        vid = p.path.lstrip("/").split("/")[0]
    if VIDEO_ID_RE.match(vid or ""):
        return "https://www.youtube.com/watch?v=" + vid
    return ""

channels = [
    {
        "name": "\u5b54\u8001\u5e2bAI\u7814\u7fd2\u793e",
        "handle": "@Teacher_Kong",
        "url": "https://www.youtube.com/@Teacher_Kong/videos",
        "channel_id": "UCpnBpREMjMNFvLTLnc2iLPQ",
    },
    {
        "name": "\u674e\u5382\u957f\u6765\u4e86",
        "handle": "@lichangzhanglaile",
        "url": "https://www.youtube.com/@lichangzhanglaile/videos",
        "channel_id": "UC0v9b0Z00wWED_vGy-Q6ibg",
    },
    {
        "name": "\u6211\u60f3\u7528Ai\u8cfa\u9322",
        "handle": "@\u6211\u60f3\u7528Ai\u8cfa\u9322",
        "url": "https://www.youtube.com/@%E6%88%91%E6%83%B3%E7%94%A8Ai%E8%B3%BA%E9%8C%A2/videos",
        "channel_id": "UCTU_nAAkekihOYA6mNUQMvQ",
    },
    {
        "name": "\u963f\u77f3OMP",
        "handle": "@ompshek",
        "url": "https://www.youtube.com/@ompshek/videos",
        "channel_id": "UCnixWoic7ATGI0AZ2LrtJ7Q",
    },
    {
        "name": "PAPAYA \u96fb\u8166\u6559\u5ba4",
        "handle": "@papayaclass",
        "url": "https://www.youtube.com/@papayaclass/videos",
        "channel_id": "UCdEpz2A4DzV__4C1x2quKLw",
    },
    {
        "name": "JayLuxAI | AI \u81ea\u52d5\u5316",
        "handle": "@JayLuxAI",
        "url": "https://www.youtube.com/@JayLuxAI/videos",
        "channel_id": "UCKxp_qMkhBTVftkhTwKJFvw",
    },
    {
        "name": "\u6cdb\u79d1\u5b78\u9662",
        "handle": "@panscischool",
        "url": "https://www.youtube.com/@panscischool/featured",
        "channel_id": "UCATnB3v_NkTTd9iD_4W2A-g",
    },
    {
        "name": "YAHA\u5b66\u5802",
        "handle": "@YAHAClass",
        "url": "https://www.youtube.com/@YAHAClass/featured",
        "channel_id": "UC7ynDhvkWzAxctvxKrkwtsg",
    },
]


def parse_pub_date(date_str):
    """Parse both RFC 2822 (RSS 2.0) and ISO 8601 (Atom) date formats \u2192 YYYY-MM-DD."""
    if not date_str:
        return ""
    try:
        # RFC 2822: "Sat, 09 May 2026 10:02:51 GMT"
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        # ISO 8601: "2026-05-09T10:02:51+00:00"
        return date_str[:10]
    except Exception:
        return date_str


def fetch_from_url(url, limit=5):
    """Fetch and parse RSS/Atom feed. Returns list of video dicts or []."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
    except Exception as e:
        print(f"    fetch error: {e}")
        return []

    try:
        root = ET.parse(io.BytesIO(raw)).getroot()
    except Exception as e:
        print(f"    parse error: {e}")
        return []

    videos = []

    # \u2500\u2500 RSS 2.0 format (RSSHub) \u2500\u2500
    items = root.findall(".//item")
    if items:
        for item in items[:limit]:
            title_el = item.find("title")
            link_el = item.find("link")
            pub_el = item.find("pubDate")
            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            pub = parse_pub_date(pub_el.text if pub_el is not None else "")
            link = safe_video_url(link)
            if title and link:
                videos.append({"title": title, "url": link, "published": pub})
        return videos

    # \u2500\u2500 Atom format (native YouTube RSS) \u2500\u2500
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    for entry in root.findall("atom:entry", ns)[:limit]:
        title_el = entry.find("atom:title", ns)
        vid_el = entry.find("yt:videoId", ns)
        pub_el = entry.find("atom:published", ns)
        if title_el is not None and vid_el is not None:
            vurl = safe_video_url("https://www.youtube.com/watch?v=" + (vid_el.text or ""))
            if not vurl:
                continue
            videos.append({
                "title": title_el.text or "",
                "url": vurl,
                "published": parse_pub_date(pub_el.text if pub_el is not None else ""),
            })
    return videos


def fetch_videos(channel_id, limit=5):
    """Try RSSHub proxy first, fall back to native YouTube RSS."""
    proxy_url = RSSHUB_BASE + channel_id
    yt_url = YT_RSS_BASE + channel_id

    print(f"  Trying RSSHub proxy...")
    videos = fetch_from_url(proxy_url, limit)
    if videos:
        print(f"  RSSHub OK: {len(videos)} videos")
        return videos

    print(f"  RSSHub failed, trying native YouTube RSS...")
    videos = fetch_from_url(yt_url, limit)
    if videos:
        print(f"  YouTube RSS OK: {len(videos)} videos")
    else:
        print(f"  Both sources failed.")
    return videos


def relative_date(date_str, now_hkt):
    try:
        pub = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        delta = now_hkt - pub
        days = delta.days
        if days == 0:
            return "Today"
        elif days == 1:
            return "1 day ago"
        elif days < 7:
            return str(days) + " days ago"
        elif days < 14:
            return "1 week ago"
        elif days < 30:
            return str(days // 7) + " weeks ago"
        elif days < 60:
            return "1 month ago"
        else:
            return str(days // 30) + " months ago"
    except Exception:
        return date_str


def safe_title(title):
    """Escape characters that could break the markdown table or inject links."""
    return (title.replace("\\", "\\\\")
                 .replace("|", r"\|").replace("\uff5c", r"\|")
                 .replace("[", r"\[").replace("]", r"\]")
                 .replace("<", "&lt;").replace(">", "&gt;"))


hkt = datetime.now(timezone(timedelta(hours=8)))
timestamp = hkt.strftime("%Y-%m-%d %H:%M HKT")
today_str = hkt.strftime("%Y-%m-%d")

# ── Load existing videos.json as fallback (in case RSS is blocked) ──
existing_videos = {}
try:
    with open("videos.json", "r", encoding="utf-8") as f:
        existing = json.load(f)
    for ch in existing.get("channels", []):
        existing_videos[ch["handle"]] = ch.get("videos", [])
    print(f"Loaded existing videos.json with {len(existing_videos)} channels as fallback.")
except Exception:
    print("No existing videos.json found, starting fresh.")

# ── Build data for videos.json ──
json_data = {
    "last_updated": timestamp,
    "channels": []
}

# ── Build markdown for README ──
lines = [
    "<!-- YOUTUBE_TRACKER_START -->",
    "## \U0001f4fa AI Learning Video Tracker",
    "",
    "*Last updated: " + timestamp + "*",
    "",
]

for ch in channels:
    print(f"\n[{ch['handle']}]")
    fetched = fetch_videos(ch["channel_id"])
    # Use fallback cache if both RSS sources failed
    if fetched:
        videos = fetched
    else:
        fallback = existing_videos.get(ch["handle"], [])
        videos = [
            {"title": v["title"], "url": safe_video_url(v.get("url", "")), "published": v["published"]}
            for v in fallback if safe_video_url(v.get("url", ""))
        ]
        if videos:
            print(f"  Using cached fallback: {len(videos)} videos")
        else:
            print(f"  No data available.")

    # JSON output
    ch_data = {
        "name": ch["name"],
        "handle": ch["handle"],
        "url": ch["url"],
        "videos": []
    }
    for v in videos:
        age = relative_date(v["published"], hkt)
        is_new = v["published"] == today_str
        ch_data["videos"].append({
            "title": v["title"],
            "url": v["url"],
            "published": v["published"],
            "age": age,
            "is_new_today": is_new,
        })
    json_data["channels"].append(ch_data)

    # Markdown output
    lines.append("### " + ch["name"] + " \u00b7 [" + ch["handle"] + "](" + ch["url"] + ")")
    lines.append("")
    lines.append("| # | Title | Age |")
    lines.append("|---|-------|-----|")
    for i, v in enumerate(videos, 1):
        title = safe_title(v["title"])
        age = relative_date(v["published"], hkt)
        lines.append("| " + str(i) + " | [" + title + "](" + v["url"] + ") | " + age + " |")
    lines.append("")

lines.append("---")
lines.append("")
lines.append("*Auto-updated every day at 00:00, 12:00 and 18:00 HKT \u00b7 [View workflow](https://github.com/LiverJust/AILearner/actions/workflows/youtube-tracker.yml)*")
lines.append("<!-- YOUTUBE_TRACKER_END -->")

tracker = "\n".join(lines)

# ── Write README.md ──
with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"<!-- YOUTUBE_TRACKER_START -->.*?<!-- YOUTUBE_TRACKER_END -->"
if re.search(pattern, content, re.DOTALL):
    new_content = re.sub(pattern, tracker, content, flags=re.DOTALL)
else:
    new_content = content.rstrip() + "\n\n" + tracker + "\n"

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_content)

# ── Write videos.json ──
with open("videos.json", "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print("README.md and videos.json updated successfully.")
