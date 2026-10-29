# Naver_rev_tool — 파인다이닝 검색 이력 뷰어

비서진 예약툴(웹 AI 검색)과 웍스 봇(파인다이닝 서치 헬퍼)에서 **어떤 조건으로 식당을 찾았고, 무엇이 추천됐는지**를 외부에서도 볼 수 있게 정리한 정적 사이트입니다.
목적은 수요(질문)와 공급(검색 가능한 파인다이닝 매장)의 간극을 보고, **어떤 업장을 먼저 예약 ON·룸 정보 등으로 셋팅해야 하는지** 정하는 것입니다.

- 공개 페이지: `https://glen-creator.github.io/Naver_rev_tool/` (GitHub Pages, `main` 브랜치 `/docs`)
- 화면: 검색 이력(필터·정렬·추천 매장) / 지도(매장·추천 횟수·동네별 수요) / 인사이트(권역×음식, 조건 빈도, 추천 TOP, 셋팅 우선 후보) / 매장 표 + 매장 상세 패널

## 구조

```
docs/
  index.html          뷰어(단일 파일, Leaflet + OpenStreetMap 타일)
  data/catalog.json   매장 카탈로그(파인다이닝 F1~F3 860곳, 좌표·룸·가격대·어워즈·리뷰 키워드, AI 검색 대상 플래그)
  data/history.json   검색 이력(질문·파싱 조건·매칭 수·추천 매장). meta.sample=true 면 샘플
scripts/
  build_catalog.py    사내 PC의 naver-board-rev-tool 빌드 산출물(index.html DATA + rt_catalog.json)에서 catalog.json 생성
  export_history.py   place-admin-api `GET /revtool/history` 에서 이력을 받아 익명화해 history.json 생성 (--sample 이면 샘플 생성)
```

## 데이터 갱신(사내망 또는 VPN에서)

```bash
python scripts/build_catalog.py
set STORE_KEY=...   # place-admin-api 저장소 키 — 실행 시점에만, 레포에 저장하지 않음
python scripts/export_history.py            # 기본: 계정을 '사용자 N' 으로 익명화
python scripts/export_history.py --names    # 메일 앞부분을 그대로 둘 때
git add docs/data && git commit -m "data: 이력 갱신 YYYY-MM-DD" && git push
```

이력 원천은 place-admin-api `revtool_history.py`(2026-10-29 추가)가 저장소 문서 `data/ask_history.json` 에 쌓는 기록입니다.
웹 검색은 캐시 히트를 포함해 질문마다, 봇은 추천 발송마다 1건씩 남고, `backfill=1` 로 컨테이너에 남은 감사 로그의 질문도 합칩니다.

## 공개 범위

- 매장 정보는 네이버 플레이스에 공개된 값(상호·주소·전화·카테고리·대표 메뉴·리뷰 키워드)과 내부 분류(티어·검색 대상 여부)만 싣습니다.
- 비서진 계정은 기본 익명화('사용자 N')되고, 메모·예약 기록·연락처 등 예약툴의 개인 데이터는 싣지 않습니다.
