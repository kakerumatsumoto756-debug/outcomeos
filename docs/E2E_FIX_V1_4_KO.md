# OutcomeOS E2E 안정성 패치 (v1.4) — 한국어 안내

이 패치는 Work 브라우저가 보고한 3가지 증상에 대응합니다.

1. **Decision 생성 기록은 있는데 목록은 0개:** 생성 POST 직후 새 ID가 해당 Workspace의 Open 목록에 실제로 보이는지 최대 세 번 검사합니다. `Link →` 버튼도 항상 서버 목록을 다시 조회합니다. POST를 자동 재시도하지 않으므로 중복 생성 위험을 피합니다.
2. **새로고침 시 `Could not reach server: 0`:** 읽기 전용 GET 요청에 한해 제한적으로 재시도하고, 서버가 불안정하면 가입 폼 대신 연결 오류/재시도 화면을 표시합니다. HTTP 응답 오류와 연결 오류는 별도 처리합니다. 로그인 성공을 보장하는 수정은 아닙니다.
3. **Panta 빈 제목·가격:** 빈 제목을 원본값인 것처럼 렌더링하지 않고 `Untitled Panta market (ID…)`로 표시합니다. Panta 상세 응답에 YES/NO 값이 없으면 `가격 없음`을 명확히 안내하며 **가짜 가격을 생성하지 않습니다**.

**새 진단 API:** 로그인한 사용자는 `/api/workspaces/<workspace_id>/diagnostics`에 GET 요청해 워크스페이스의 `open_decisions`, `audit_create_events`, `recent_ids`를 비교할 수 있습니다. ID만 포함하고 이메일/비밀번호/개인 메모는 반환하지 않습니다. 실제 Decision과 Activity Log의 불일치가 재현된다면 이 JSON과 Vercel 로그의 상태 코드만 공유하세요.

## 안전하게 기존 저장소에 적용

현재 폴더 `~/projects/outcomeos-deploy`에 GitHub의 최신 `main`이 있다고 가정합니다. **ZIP 패치 안에는 `.git`, DB 파일, `.env`가 없습니다.**

```bash
cd ~/projects/outcomeos-deploy
git pull --ff-only origin main
python3 -m zipfile -e "/mnt/c/Users/YOUR_WINDOWS_USER/Downloads/OutcomeOS-E2E-FIX-PATCH.zip" .
find . -type f -name '*:Zone.Identifier' -not -path './.git/*' -delete
python3 -m unittest discover -s tests -q
node tests/test_client_regressions.cjs
node --check web/app.js
git status --short
git diff --check
git add app/http_api.py app/panta.py web/app.js web/style.css tests/test_outcomeos.py tests/test_client_regressions.cjs docs/E2E_FIX_V1_4_KO.md
git diff --cached --stat
git commit -m "Improve decision consistency, session recovery and Panta data clarity"
git push origin main
```

Windows 사용자 폴더 이름을 `YOUR_WINDOWS_USER` 대신 입력하세요. 이미 구 버전 파일에 변경 사항이 있으면 덮어쓰기 전에 `git diff`로 확인하세요. **절대로 `git push --force`를 사용하지 마세요.**

## Vercel 및 Work 재검증

1. Vercel Deployments에서 최신 `main` 커밋이 `Ready`인지 확인합니다.
2. 시크릿/일반 Chrome에서 로그인 후 임의의 테스트 Decision을 1개만 만듭니다.
3. Decision rooms 목록에 방금 만든 ID와 제목이 나타나는지 확인합니다.
4. Market intelligence → Live Panta → Fetch → Link를 눌러 방 선택이 가능한지 확인합니다.
5. 새로고침 후 세션이 유지되는지 확인합니다. 일시적 장애라면 전용 재시도 화면이 표시되는지 확인합니다.
6. Panta 상세 화면의 YES/NO 값이 없으면 없는 그대로 표시합니다. 이는 상용 가격 피드 실패와 동의어가 아닙니다.
7. Forecast / 공유 Report / 시크릿 창 접근을 마지막에 점검합니다.

**현재 판정: 제출 준비 보류.** 이 패치는 로컬 자동 테스트만 완료했습니다. Vercel + Neon 실환경과 Work 브라우저 End-to-End 테스트는 다시 해야 합니다. API Key와 Neon 비밀번호는 절대 공유하지 마세요.
