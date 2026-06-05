import os
import json
import requests
from datetime import datetime, timezone, timedelta
from jinja2 import Template

API_KEY   = os.environ.get("FOOTBALL_API_KEY", "")
BASE_URL  = "https://api.football-data.org/v4"
HEADERS   = {"X-Auth-Token": API_KEY}
KST       = timezone(timedelta(hours=9))
COMPETITION_CODE = "WC"
KOREA_TEAM_ID = 732

def fetch_korea_matches():
    url = f"{BASE_URL}/teams/{KOREA_TEAM_ID}/matches"
    params = {"competitions": COMPETITION_CODE, "status": "SCHEDULED,IN_PLAY,PAUSED,FINISHED"}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("matches", [])
    except Exception as e:
        print(f"[경고] 한국 경기 API 실패: {e}")
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
        print(f"[경고] 순위표 API 실패: {e}")
        return []

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
        kst = dt.astimezone(KST)
        return kst.strftime("%-m/%-d %H:%M")
    except:
        return utc_str

def fmt_kst_iso(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        kst = dt.astimezone(KST)
        return kst.isoformat()
    except:
        return ""

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

if __name__ == "__main__":
    print("▶ 데이터 수집 시작...")
    raw_matches   = fetch_korea_matches()
    raw_standings = fetch_group_standings()
    matches   = process_matches(raw_matches)
    standings = process_standings(raw_standings)
    next_m    = next_korea_match(matches)
    last_m    = last_korea_match(matches)
    updated   = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"matches": matches, "standings": standings,
                   "next_match": next_m, "last_match": last_m,
                   "updated_at": updated}, f, ensure_ascii=False, indent=2)

    tmpl = Template(open("template.html").read())
    html = tmpl.render(matches=matches, standings=standings,
                       next_match=next_m, last_match=last_m,
                       updated_at=updated)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 완료: {updated}")
