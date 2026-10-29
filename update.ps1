# 파인다이닝 검색 이력 뷰어 — 데이터 갱신 원클릭 (Windows PowerShell 5.1)
#   실행:  & C:\Users\USER\Glen_Claude_code\Naver_rev_tool\update.ps1
#   하는 일: ① n3r 에서 STORE_KEY 를 읽어 서버 이력 내보내기(history.json) ② 카탈로그 재생성(catalog.json, 원천 있을 때만) ③ 바뀐 데이터 커밋·푸시
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "① 서버 이력 내보내기 (--from-n3r)" -ForegroundColor Cyan
python scripts\export_history.py --from-n3r
if ($LASTEXITCODE -ne 0) { Write-Host "내보내기 실패 — 위 메시지를 확인하세요." -ForegroundColor Red; exit 1 }

$src = Join-Path (Split-Path -Parent $root) "naver-board-rev-tool\index.html"
if (Test-Path $src) {
    Write-Host "② 카탈로그 재생성" -ForegroundColor Cyan
    python scripts\build_catalog.py
    if ($LASTEXITCODE -ne 0) { Write-Host "카탈로그 생성 실패(이력만 반영합니다)" -ForegroundColor Yellow }
}

Write-Host "③ 커밋·푸시" -ForegroundColor Cyan
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "변경된 데이터가 없습니다(이미 최신)." -ForegroundColor Yellow
} else {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    git commit -q -m "data: 이력·카탈로그 갱신 $stamp"
}
git push origin main
Write-Host "완료 — https://glen-creator.github.io/Naver_rev_tool/ (반영까지 1~2분)" -ForegroundColor Green
