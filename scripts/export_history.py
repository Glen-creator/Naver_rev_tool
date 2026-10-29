"""AI 검색 이력 내보내기 — docs/data/history.json

라이브 모드(사내망/VPN 필요):
  set STORE_KEY=<place-admin-api 저장소 키>      ← 코드·레포에 저장하지 말고 실행 시점에만
  python scripts/export_history.py --from-n3r        ← 키를 n3r app env 에서 자동으로 읽음(권장)
  python scripts/export_history.py [--api https://place-admin.io.naver.com] [--since 2026-10-01] [--names]
  → GET {api}/revtool/history?backfill=1 을 받아 계정 메일을 익명화(사용자 1, 2, …)해 저장한다. --names 를 주면 메일 앞부분을 그대로 둔다.

샘플 모드(네트워크 불필요, 뷰어 개발·시연용):
  python scripts/export_history.py --sample
  → 질문 40건을 봇과 같은 매칭 로직(place-admin-api/works_bot.py 의 passes/score/relax)으로 로컬 카탈로그에 대조해 만든다.
     history.json 의 meta.sample=true 가 되고 뷰어 상단에 '샘플 데이터' 배너가 뜬다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "data", "history.json")
API_DIR = os.path.join(HERE, "..", "..", "place-admin-api")
CAT_FILE = os.path.join(HERE, "..", "..", "naver-board-rev-tool", "data", "rt_catalog.json")


def anonymize(entries: list, keep_names: bool) -> list:
    order: dict = {}
    for e in entries:
        who = (e.get("who") or "guest").lower()
        if who in ("guest", "") or "@" not in who:
            e["who"] = "guest" if who in ("guest", "") else "미등록"
            continue
        if keep_names:
            e["who"] = who.split("@")[0]
            continue
        if who not in order:
            order[who] = len(order) + 1
        e["who"] = f"사용자 {order[who]}"
        e["who_key"] = hashlib.sha1(who.encode()).hexdigest()[:8]   # 같은 사람 식별용(메일 역산 불가)
    return entries


def _find_key(obj, name="STORE_KEY"):
    """n3r app env 출력(JSON)에서 name 항목의 값을 찾는다 — {name:…,value:…} 목록이든 {NAME: value} 사전이든."""
    if isinstance(obj, dict):
        if (obj.get("name") == name or obj.get("key") == name) and obj.get("value"):   # n3r app env -o json 은 {key,value,encrypted}
            return str(obj["value"])
        if obj.get(name) and isinstance(obj[name], str):
            return obj[name]
        for v in obj.values():
            r = _find_key(v, name)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, name)
            if r:
                return r
    return ""


def key_from_n3r(app: str) -> str:
    """n3r CLI 로 place-admin-api 의 STORE_KEY 를 읽는다(값은 메모리에서만 쓰고 출력하지 않는다)."""
    import re
    import shutil
    import subprocess
    exe = next((w for w in (shutil.which(n) for n in ("n3r", "n3r.exe", "n3r.cmd")) if w), None)
    if not exe:
        sys.exit("n3r CLI 를 PATH 에서 찾지 못했습니다.")
    try:
        r = subprocess.run([exe, "app", "env", app, "-o", "json"], cwd=API_DIR, capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        sys.exit(f"n3r 실행 실패: {e}")
    out = re.sub(r"\[[0-9;]*[A-Za-z]", "", r.stdout or "")   # 색상 코드 제거(ANSI 시퀀스의 '[' 가 JSON 추출을 어긋나게 함)
    m = re.search(r"[\[{].*[\]}]", out, re.S)
    key = ""
    if m:
        try:
            key = _find_key(json.loads(m.group(0)))
        except ValueError:
            key = ""
    if not key:
        m2 = re.search(r"STORE_KEY\s*[:=]?\s*([A-Za-z0-9_\-./+=]{8,})", out + (r.stderr or ""))
        key = m2.group(1) if m2 else ""
    if not key:
        sys.exit("n3r app env 출력에서 STORE_KEY 를 찾지 못했습니다 (n3r 로그인·프로젝트 선택 상태를 확인하세요).")
    return key


def live(api: str, since: str, keep_names: bool, from_n3r: bool = False, app: str = "place-admin-api-st") -> dict:
    import requests
    key = os.environ.get("STORE_KEY", "").strip()
    if from_n3r or not key:
        key = key_from_n3r(app)
    if not key:
        sys.exit("환경변수 STORE_KEY 가 없습니다 (실행 시점에만 set 하거나 --from-n3r 를 쓰세요).")
    if not key.isascii() or key.startswith("<") or key in ("키", "<키>"):
        sys.exit("STORE_KEY 가 자리표시자('<키>') 그대로입니다 — place-admin-api(n3r) 의 STORE_KEY 환경변수 값을 넣어 주세요.")
    r = requests.get(api.rstrip("/") + "/revtool/history", params={"backfill": 1, "since": since, "limit": 10000},
                     headers={"X-Store-Key": key}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"내보내기 실패 HTTP {r.status_code}: {r.text[:200]}")
    j = r.json()
    ent = anonymize(j.get("entries", []), keep_names)
    return {"asof": j.get("asof"), "since": j.get("since"), "catalog_asof": j.get("catalog_asof"), "n": len(ent),
            "meta": {"sample": False, "anonymized": not keep_names}, "entries": ent}


# ---------- 샘플 ----------
SAMPLE_QS = [
    ("강남권 미쉐린 파인다이닝 룸 내일 19시 4명", {"area": ["강남·서초"], "michelin": True, "room": True, "people": 4, "time": "19:00", "occasion": "접대", "summary": "강남 미쉐린 룸 4명 접대"}),
    ("청담 한우 오마카세 6명 룸 있는 곳", {"hood": ["청담·압구정"], "food": ["한우"], "omakase": True, "room": True, "people": 6, "summary": "청담 한우 오마카세 룸 6명"}),
    ("판교 점심 미팅 8명 조용한 방", {"hood": ["판교"], "room": True, "people": 8, "time": "12:00", "occasion": "미팅", "summary": "판교 점심 미팅 8명 룸"}),
    ("정자역 근처 저녁 회식 20명 대관 가능한 곳", {"hood": ["정자"], "rent": True, "people": 20, "time": "19:00", "occasion": "회식", "summary": "정자 회식 20명 대관"}),
    ("광화문 외부 접대 일식 룸 4명 금요일 저녁", {"area": ["광화문·도심"], "food": ["일식"], "room": True, "people": 4, "time": "19:00", "occasion": "접대", "michelin": True, "summary": "광화문 일식 룸 접대"}),
    ("여의도 양식 10만원 이하 6명", {"area": ["용산·성수·여의도"], "food": ["양식"], "price": ["~3만", "3~5만", "5~10만"], "people": 6, "summary": "여의도 양식 10만원 이하"}),
    ("한남동 프렌치 데이트 2명 20만원 이상", {"hood": ["한남·이태원"], "food": ["양식"], "price": ["20만↑"], "people": 2, "occasion": "데이트", "summary": "한남 프렌치 하이엔드"}),
    ("부산 해운대 스시 오마카세 4명", {"area": ["부산"], "food": ["일식"], "omakase": True, "people": 4, "summary": "부산 스시 오마카세 4명"}),
    ("잠실 롯데 근처 중식 룸 12명", {"hood": ["잠실"], "food": ["중식"], "room": True, "people": 12, "summary": "잠실 중식 룸 12명"}),
    ("역삼 코엑스 근처 저녁 접대 미쉐린 스타 4명", {"hood": ["역삼·선릉·삼성"], "michelin": True, "people": 4, "time": "19:00", "occasion": "접대", "summary": "역삼 미쉐린 접대"}),
    ("서래마을 이탈리안 가족 모임 5명 룸", {"hood": ["서초·반포·방배"], "food": ["양식"], "room": True, "people": 5, "occasion": "가족", "summary": "서래마을 이탈리안 가족 룸"}),
    ("성수동 와인바 분위기 좋은 곳 4명", {"hood": ["성수"], "food": ["바·라운지"], "people": 4, "summary": "성수 와인바 4명"}),
    ("을지로 한식 점심 6명 15만원 정도", {"hood": ["광화문·시청", "을지로·명동"], "food": ["한식"], "price": ["10~20만"], "people": 6, "time": "12:00", "summary": "을지로 한식 점심"}),
    ("강남역 양재 한식 파인다이닝 룸 7명 내일", {"hood": ["강남역·양재"], "food": ["한식"], "fd": True, "room": True, "people": 7, "summary": "강남역 한식 파인 룸 7명"}),
    ("신사 가로수길 일식 오마카세 2명 저녁", {"hood": ["신사·논현"], "food": ["일식"], "omakase": True, "people": 2, "time": "19:00", "summary": "가로수길 오마카세 2명"}),
    ("속초 바닷가 회식 15명", {"place": "속초", "people": 15, "occasion": "회식", "summary": "속초 회식 15명"}),
    ("제주 애월 가족 식사 6명", {"place": "제주 애월", "people": 6, "occasion": "가족", "summary": "제주 가족 식사"}),
    ("판교 양식 대관 30명 송년회", {"hood": ["판교"], "food": ["양식"], "rent": True, "people": 30, "occasion": "회식", "summary": "판교 양식 대관 30명"}),
    ("청담 프렌치 미쉐린 2스타 4명 룸", {"hood": ["청담·압구정"], "food": ["양식"], "michelin": True, "room": True, "people": 4, "summary": "청담 미쉐린 프렌치 룸"}),
    ("용산 한우 구이 회식 10명 룸", {"hood": ["용산·한강로"], "food": ["한우"], "room": True, "people": 10, "occasion": "회식", "summary": "용산 한우 회식 룸 10명"}),
    ("분당 서현 중식 가성비 8명", {"hood": ["서현·수내·야탑"], "food": ["중식"], "price": ["~3만", "3~5만"], "people": 8, "summary": "서현 중식 가성비"}),
    ("내일 저녁 7시반 강남 파인다이닝 3명 예약 가능한 곳", {"area": ["강남·서초"], "fd": True, "people": 3, "time": "19:30", "avail": True, "summary": "강남 파인 3명 빈자리"}),
    ("광화문 아시안 점심 4명", {"area": ["광화문·도심"], "food": ["아시안"], "people": 4, "time": "12:00", "summary": "광화문 아시안 점심"}),
    ("압구정 스시 오마카세 룸 4명 20만원 이상", {"hood": ["청담·압구정"], "food": ["일식"], "omakase": True, "room": True, "price": ["20만↑"], "people": 4, "summary": "압구정 하이엔드 오마카세 룸"}),
    ("여의도 IFC 근처 양식 미팅 6명 룸", {"hood": ["여의도"], "food": ["양식"], "room": True, "people": 6, "occasion": "미팅", "summary": "여의도 양식 미팅 룸"}),
    ("정자 네이버 1784 근처 점심 일식 4명", {"hood": ["정자"], "food": ["일식"], "people": 4, "time": "12:00", "summary": "정자 일식 점심 4명"}),
    ("강남 한식 코스 접대 룸 8명 10~20만", {"area": ["강남·서초"], "food": ["한식"], "room": True, "people": 8, "price": ["10~20만"], "occasion": "접대", "summary": "강남 한식 코스 접대"}),
    ("부산 서면 한우 10명 룸", {"area": ["부산"], "food": ["한우"], "room": True, "people": 10, "summary": "부산 한우 룸 10명"}),
    ("삼성동 중식 미쉐린 6명", {"hood": ["역삼·선릉·삼성"], "food": ["중식"], "michelin": True, "people": 6, "summary": "삼성동 중식 미쉐린"}),
    ("서초 반포 양식 브런치 가족 4명", {"hood": ["서초·반포·방배"], "food": ["양식"], "people": 4, "occasion": "가족", "summary": "반포 양식 가족"}),
    ("대전 출장 저녁 접대 6명", {"place": "대전", "people": 6, "occasion": "접대", "summary": "대전 접대 6명"}),
    ("성수 한식 파인다이닝 4명 저녁", {"hood": ["성수"], "food": ["한식"], "fd": True, "people": 4, "time": "19:00", "summary": "성수 한식 파인"}),
    ("판교 일식 룸 미팅 5명 점심 5만원대", {"hood": ["판교"], "food": ["일식"], "room": True, "people": 5, "time": "12:00", "price": ["5~10만"], "occasion": "미팅", "summary": "판교 일식 점심 룸"}),
    ("청담 대관 가능한 양식 25명", {"hood": ["청담·압구정"], "food": ["양식"], "rent": True, "people": 25, "summary": "청담 양식 대관 25명"}),
    ("명동 시청 일식 접대 룸 4명", {"hood": ["광화문·시청", "을지로·명동"], "food": ["일식"], "room": True, "people": 4, "occasion": "접대", "summary": "시청 일식 접대 룸"}),
    ("한남 바 라운지 2차 8명", {"hood": ["한남·이태원"], "food": ["바·라운지"], "people": 8, "summary": "한남 라운지 8명"}),
    ("강남 미쉐린 파인다이닝 룸 10명 내일 저녁", {"area": ["강남·서초"], "michelin": True, "room": True, "people": 10, "time": "19:00", "summary": "강남 미쉐린 룸 10명"}),
    ("분당 한우 오마카세 4명", {"area": ["분당·판교"], "food": ["한우"], "omakase": True, "people": 4, "summary": "분당 한우 오마카세"}),
    ("잠실 시그니엘 근처 프렌치 데이트 2명", {"hood": ["잠실"], "food": ["양식"], "people": 2, "occasion": "데이트", "summary": "잠실 프렌치 데이트"}),
    ("광화문 한식 룸 12명 회식 가성비", {"area": ["광화문·도심"], "food": ["한식"], "room": True, "people": 12, "occasion": "회식", "price": ["~3만", "3~5만"], "summary": "광화문 한식 회식 룸"}),
]


def sample() -> dict:
    sys.path.insert(0, API_DIR)
    import works_bot  # noqa: E402  (place-admin-api 의 매칭 로직 재사용)
    cat = json.load(open(CAT_FILE, encoding="utf-8"))
    works_bot.catalog = lambda force=False: cat
    hoods = {h["hood"] for h in cat["meta"]["hoods"]}
    rnd = random.Random(20261029)
    users = ["사용자 1", "사용자 2", "사용자 3", "사용자 4", "사용자 5", "사용자 6"]
    base = dt.datetime(2026, 10, 13, 9, 0)
    entries = []
    for i, (q, p) in enumerate(SAMPLE_QS):
        p = dict(p)
        p["hood"] = [h for h in p.get("hood", []) if h in hoods]
        ts = base + dt.timedelta(days=rnd.randint(0, 15), hours=rnd.randint(0, 10), minutes=rnd.randint(0, 59))
        if not p.get("date") and rnd.random() < 0.6:
            p["date"] = (ts + dt.timedelta(days=rnd.randint(1, 10))).date().isoformat()
        pp = dict(p)
        relaxed = []
        rows = [d for d in cat["entries"] if works_bot.passes(d, pp)]
        while not rows:
            m = works_bot.relax(pp)
            if not m:
                break
            relaxed.append(m)
            rows = [d for d in cat["entries"] if works_bot.passes(d, pp)]
        rows.sort(key=lambda d: -works_bot.score(d, pp))
        src = "bot" if rnd.random() < 0.45 else "web"
        top = [{"pid": d["pid"], "name": d["name"], "score": round(works_bot.score(d, pp), 1)} for d in rows[:12]]
        if src == "bot":
            for k, t in enumerate(top[:3]):
                t["rank"] = rnd.choice([0, 0, 1, 2, 3])
        entries.append({"id": f"sample-{i:03d}", "ts": ts.isoformat(timespec="seconds"), "src": src, "who": rnd.choice(users),
                        "q": q, "parsed": {k: v for k, v in p.items() if v not in (None, "", [], False)},
                        "top": top, "n_match": len(rows), "relaxed": relaxed, "ms": rnd.randint(350, 2400)})
    entries.sort(key=lambda e: e["ts"])
    return {"asof": dt.datetime.now().isoformat(timespec="seconds"), "since": entries[0]["ts"], "catalog_asof": cat.get("asof", ""),
            "n": len(entries), "meta": {"sample": True, "anonymized": True}, "entries": entries}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="https://place-admin.io.naver.com")
    ap.add_argument("--since", default="")
    ap.add_argument("--names", action="store_true", help="계정 메일 앞부분을 그대로 둔다(기본은 사용자 N 익명화)")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--from-n3r", action="store_true", help="STORE_KEY 를 n3r app env 에서 직접 읽는다(키 복사 불필요)")
    ap.add_argument("--app", default="place-admin-api-st", help="n3r 앱 이름")
    a = ap.parse_args()
    out = sample() if a.sample else live(a.api, a.since, a.names, a.from_n3r, a.app)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"history.json: {out['n']}건 (sample={out['meta']['sample']}) → {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
