"""공개 뷰어용 매장 카탈로그 생성 — docs/data/catalog.json

원천(사내 PC 로컬): Glen_Claude_code/naver-board-rev-tool
  - index.html 의 DATA(빌드된 예약툴 매장 860곳: 세일즈 어드민 피라미드 F1~F3 파인다이닝, 좌표·룸·가격대·어워즈·리뷰 포함)
  - data/rt_catalog.json 의 meta(권역·동네 중심 좌표) + entries(봇/AI 검색 대상 171곳 → searchable 플래그)
공개 레포에는 매장 공개 정보만 싣는다(비서진 메모·예약 기록·계정 정보는 싣지 않음).

사용: python scripts/build_catalog.py [--src <naver-board-rev-tool 경로>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "data", "catalog.json")
DEFAULT_SRC = os.path.join(HERE, "..", "..", "naver-board-rev-tool")


def load_data(src: str) -> list:
    html = open(os.path.join(src, "index.html"), encoding="utf-8").read()
    m = re.search(r"const DATA=(\[.*?\]);\n", html, re.S)
    if not m:
        sys.exit("index.html 에서 DATA 를 찾지 못했습니다")
    return json.loads(m.group(1))


def slim(v: dict, searchable: set) -> dict:
    rw = v.get("rw") or {}
    pr = v.get("price") or {}
    aw = v.get("aw") or {}
    return {
        "pid": v["pid"], "name": v.get("name", ""),
        "x": float(v["x"]) if v.get("x") else None, "y": float(v["y"]) if v.get("y") else None,
        "hood": v.get("hood") or "", "area": v.get("area") or "", "region": v.get("region") or "",
        "addr": v.get("addr") or "", "food": v.get("food") or "", "pcCat": v.get("pcCat") or "",
        "room": v.get("room") or "", "cap": v.get("cap") or "", "capmax": v.get("capmax") or 0, "rent": v.get("rent") or "",
        "booking": bool(v.get("booking")), "burl": v.get("burl") or "",
        "tier": v.get("fdt") or "", "mi": v.get("mi") or "", "prio": v.get("prio") or "",
        "pv": v.get("pv") or 0, "pb": pr.get("band") or "", "plo": pr.get("lo"), "phi": pr.get("hi"),
        "repr": [[n, p] for n, p in (pr.get("repr") or [])[:3]],
        "oma": bool(v.get("oma")), "meat": bool(v.get("meat")), "closed": bool(v.get("bs")),
        "photo": v.get("photo") or "", "phone": v.get("phone") or "",
        "awards": sorted(aw.keys()) if isinstance(aw, dict) else [],
        "rwn": rw.get("n") or 0, "rwsc": rw.get("sc"), "kw": [k for k, _ in (rw.get("kw") or [])[:4]],
        "seat": [s for s in (rw.get("seat") or [])[:4]],
        "searchable": v["pid"] in searchable,   # AI 검색·봇 카탈로그(rt_catalog.json) 포함 여부 — 신규 편입(fd)·검색 제외분은 false
        "new": bool(v.get("fd")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    a = ap.parse_args()
    data = load_data(a.src)
    cat = json.load(open(os.path.join(a.src, "data", "rt_catalog.json"), encoding="utf-8"))
    searchable = {e["pid"] for e in cat.get("entries", [])}
    rows = [slim(v, searchable) for v in data]
    out = {"asof": dt.date.today().isoformat(), "source_asof": cat.get("asof", ""), "n": len(rows),
           "n_searchable": sum(1 for r in rows if r["searchable"]),
           "meta": cat.get("meta", {}), "entries": rows}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"catalog.json: {len(rows)}곳 (검색 대상 {out['n_searchable']}) → {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
