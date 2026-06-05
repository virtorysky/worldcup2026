import os
import json
import requests
import base64
from datetime import datetime, timezone, timedelta
from jinja2 import Template

API_KEY   = os.environ.get("FOOTBALL_API_KEY", "")
BASE_URL  = "https://api.football-data.org/v4"
HEADERS   = {"X-Auth-Token": API_KEY}
KST       = timezone(timedelta(hours=9))
COMPETITION_CODE = "WC"
KOREA_TEAM_ID = 732

# 워드프레스 설정
WP_DOMAIN   = "https://news.simple-life6.com"
WP_USER     = os.environ.get("WP_USER", "")
WP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
WP_PAGE_SLUG = "worldcup2026"  # 워드프레스 페이지 슬러그

FALLBACK_MATCHES = [
    {
        "home": "Korea Republic", "away": "Costa Rica",
        "home_flag": "🇰🇷", "away_flag": "🇨🇷",
        "status": "SCHEDULED",
        "score_h": "-", "score_a": "-",
        "date_kst": "6/16 04:00", "date_iso": "2026-06-16T04:00:00+09:00",
        "is_korea": True, "matchday": 1,
    },
    {
        "home": "Korea Republic", "away": "Mexico",
        "home_flag": "🇰🇷", "away_flag": "🇲🇽",
        "status": "SCHEDULED",
        "score_h": "-", "score_a": "-",
        "date_kst": "6/21 04:00", "date_iso": "2026-06-21T04:00:00+09:00",
        "is_korea": True, "matchday": 2,
    },
    {
        "home": "Germany", "away": "Korea Republic",
        "home_flag": "🇩🇪", "away_flag": "🇰🇷",
        "status": "SCHEDULED",
        "score_h": "-", "score_a": "-",
        "date_kst": "6/25 07:00", "date_iso": "2026-06-25T07:00:00+09:00",
        "is_korea": True, "matchday": 3,
    },
]

FALLBACK_STANDINGS = [
    {"position":1,"name":"Germany","flag":"🇩🇪","played":0,"won":0,"draw":0,"lost":0,"gd":0,"points":0,"is_korea":False},
    {"position":2,"name":"Korea Republic","flag":"🇰🇷","played":0,"won":0,"draw":0,"lost":0,"gd":0,"points":0,"is_korea":True},
    {"position":3,"name":"Mexico","flag":"🇲🇽","played":0,"won":0,"draw":0,"lost":0,"gd":0,"points":0,"is_korea":False},
    {"position":4,"name":"Costa Rica","flag":"🇨🇷","played":0,"won":0,"draw":0,"lost":0,"gd":0,"points":0,"is_korea":False},
]

FLAG_MAP = {
    "Korea Republic": "🇰🇷", "South Korea": "🇰🇷",
    "Germany": "🇩🇪", "Mexico": "🇲🇽", "Costa Rica": "🇨🇷",
    "Brazil": "🇧🇷", "Argentina": "🇦🇷", "France": "🇫🇷",
    "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Portugal": "🇵🇹",
    "Japan": "🇯🇵", "USA": "🇺🇸", "Netherlands": "🇳🇱",
}

def get_flag(name):
    for k, v in FLAG_MAP.items():
        if k.lower() in name.lower():
            return v
    return "🏳️"

def fmt_kst(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%-m/%-d %H:%M")
    except:
        return utc_str

def fmt_kst_iso(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.astimezone(KST).isoformat()
    except:
        return ""

def fetch_korea_matches():
    url = f"{BASE_URL}/teams/{KOREA_TEAM_ID}/matches"
    params = {"competitions": COMPETITION_CODE, "status": "SCHEDULED,IN_PLAY,PAUSED,FINISHED"}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("matches", [])
        print(f"  API 경기 데이터: {len(data)}개")
        return data
    except Exception as e:
        print(f"  [경고] 경기 API 실패: {e}")
        return []

def fetch_group_standings():
    url = f"{BASE_URL}/competitions/{COMPETITION_CODE}/standings"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        standings = r.json().get("standings", [])
        for s in standings:
            if s.get("type") == "TOTAL":
                for group in s.get("groups", []):
                    teams = [t["team"]["name"] for t in group.get("table", [])]
                    if "Korea Republic" in teams or "South Korea" in teams:
                        return group.get("table", [])
        return []
    except Exception as e:
        print(f"  [경고] 순위표 API 실패: {e}")
        return []

def process_matches(raw):
    result = []
    for m in raw:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        status = m["status"]
        score_h = m["score"]["fullTime"]["home"]
        score_a = m["score"]["fullTime"]["away"]
        utc_date = m.get("utcDate", "")
        is_korea = "Korea" in home or "Korea" in away
        result.append({
            "home": home, "away": away,
            "home_flag": get_flag(home), "away_flag": get_flag(away),
            "status": status,
            "score_h": score_h if score_h is not None else "-",
            "score_a": score_a if score_a is not None else "-",
            "date_kst": fmt_kst(utc_date),
            "date_iso": fmt_kst_iso(utc_date),
            "is_korea": is_korea,
            "matchday": m.get("matchday", ""),
        })
    return result

def process_standings(raw):
    result = []
    for row in raw:
        name = row["team"]["name"]
        result.append({
            "position": row["position"], "name": name,
            "flag": get_flag(name),
            "played": row["playedGames"], "won": row["won"],
            "draw": row["draw"], "lost": row["lost"],
            "gd": row["goalDifference"], "points": row["points"],
            "is_korea": "Korea" in name,
        })
    return result

def next_korea_match(matches):
    for m in matches:
        if m["is_korea"] and m["status"] == "SCHEDULED":
            return m
    return None

def last_korea_match(matches):
    finished = [m for m in matches if m["is_korea"] and m["status"] == "FINISHED"]
    return finished[-1] if finished else None

def get_wp_page_id(slug):
    """슬러그로 워드프레스 페이지 ID 조회"""
    url = f"{WP_DOMAIN}/wp-json/wp/v2/pages?slug={slug}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        pages = r.json()
        if pages:
            print(f"  워드프레스 페이지 ID: {pages[0]['id']}")
            return pages[0]["id"]
        print(f"  [경고] 슬러그 '{slug}' 페이지 없음 → 새 페이지 생성")
        return None
    except Exception as e:
        print(f"  [경고] 페이지 ID 조회 실패: {e}")
        return None

def push_to_wordpress(html_content):
    """워드프레스 페이지 생성 또는 업데이트"""
    token = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }

    page_id = get_wp_page_id(WP_PAGE_SLUG)

    payload = {
        "title": "2026 월드컵 한국 경기 올인원 | 일정·결과·중계",
        "content": html_content,
        "status": "publish",
        "slug": WP_PAGE_SLUG,
    }

    try:
        if page_id:
            # 기존 페이지 업데이트
            url = f"{WP_DOMAIN}/wp-json/wp/v2/pages/{page_id}"
            r = requests.put(url, headers=headers, json=payload, timeout=30)
        else:
            # 새 페이지 생성
            url = f"{WP_DOMAIN}/wp-json/wp/v2/pages"
            r = requests.post(url, headers=headers, json=payload, timeout=30)

        r.raise_for_status()
        result = r.json()
        print(f"  ✅ 워드프레스 업데이트 완료: {result.get('link', '')}")
        return True
    except Exception as e:
        print(f"  [오류] 워드프레스 업데이트 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  응답: {e.response.text[:300]}")
        return False

if __name__ == "__main__":
    print("▶ 데이터 수집 시작...")

    raw_matches   = fetch_korea_matches()
    raw_standings = fetch_group_standings()

    matches   = process_matches(raw_matches) if raw_matches else FALLBACK_MATCHES
    standings = process_standings(raw_standings) if raw_standings else FALLBACK_STANDINGS

    print(f"  경기 데이터: {'API' if raw_matches else '백업'} 사용")
    print(f"  순위표 데이터: {'API' if raw_standings else '백업'} 사용")

    next_m  = next_korea_match(matches)
    last_m  = last_korea_match(matches)
    updated = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"matches": matches, "standings": standings,
                   "next_match": next_m, "last_match": last_m,
                   "updated_at": updated}, f, ensure_ascii=False, indent=2)

    # GitHub Pages용 HTML 생성
    tmpl = Template(open("template.html").read())
    html = tmpl.render(matches=matches, standings=standings,
                       next_match=next_m, last_match=last_m,
                       updated_at=updated)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ index.html 생성 완료")

    # 워드프레스에 푸시 (애드센스 코드 포함된 template 사용)
    tmpl_wp = Template(open("template_wp.html").read())
    html_wp = tmpl_wp.render(matches=matches, standings=standings,
                              next_match=next_m, last_match=last_m,
                              updated_at=updated)
    print("▶ 워드프레스 업데이트 시작...")
    push_to_wordpress(html_wp)

    print(f"✅ 전체 완료: {updated}")
