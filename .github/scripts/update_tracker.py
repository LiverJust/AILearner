import urllib.request
import xml.etree.ElementTree as ET
import re
import json
from datetime import datetime, timezone, timedelta

channels = [
    {
        "name": "\u5b54\u8001\u5e2bAI\u7814\u7fd2\u793e",
        "handle": "@Teacher_Kong",
        "url": "https://www.youtube.com/@Teacher_Kong/videos",
        "rss": "https://www.youtube.com/feeds/videos.xml?channel_id=UCpnBpREMjMNFvLTLnc2iLPQ",
    },
    {
        "name": "\u674e\u5382\u957f\u6765\u4e86",
        "handle": "@lichangzhanglaile",
        "url": "https://www.youtube.com/@lichangzhanglaile/videos",
        "rss": "https://www.youtube.com/feeds/videos.xml?channel_id=UC0v9b0Z00wWED_vGy-Q6ibg",
    },
    {
        "name": "\u6211\u60f3\u7528Ai\u8cfa\u9322",
        "handle": "@\u6211\u60f3\u7528Ai\u8cfa\u9322",
        "url": "https://www.youtube.com/@%E6%88%91%E6%83%B3%E7%94%A8Ai%E8%B3%BA%E9%8C%A2/videos",
        "rss": "https://www.youtube.com/feeds/videos.xml?channel_id=UCTU_nAAkekihOYA6mNUQMvQ",
    },
    {
        "name": "\u963f\u77f3OMP",
        "handle": "@ompshek",
        "url": "https://www.youtube.com/@ompshek/videos",
        "rss": "https://www.youtube.com/feeds/videos.xml?channel_id=UCnixWoic7ATGI0AZ2LrtJ7Q",
    },
]


def fetch_videos(rss_url, limit=5):
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            tree = ET.parse(r)
    except Exception as e:
        print(f"ERROR fetching {rss_url}: {e}")
        return []
    root = tree.getroot()
    videos = []
    for entry in root.findall("atom:entry", ns)[:limit]:
        title_el = entry.find("atom:title", ns)
        vid_el = entry.find("yt:videoId", ns)
        pub_el = entry.find("atom:published", ns)
        if title_el is not None and vid_el is not None:
            videos.append(
                {
                    "title": title_el.text or "",
                    "url": "https://www.youtube.com/watch?v=" + (vid_el.text or ""),
                    "published": (pub_el.text or "")[:10],
                }
            )
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
    return title.replace("|", r"\|").replace("\uff5c", r"\|")


hkt = datetime.now(timezone(timedelta(hours=8)))
timestamp = hkt.strftime("%Y-%m-%d %H:%M HKT")
today_str = hkt.strftime("%Y-%m-%d")

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
    videos = fetch_videos(ch["rss"])

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
lines.append("*Auto-updated every day at 12:00 and 18:00 HKT \u00b7 [View workflow](https://github.com/LiverJust/AILearner/actions/workflows/youtube-tracker.yml)*")
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
