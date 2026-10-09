# OutcomeOS v1.5 — 통합 코드 감사 및 최종 패치

기준: GitHub `main` 커밋 `fbf6a8b` (OutcomeOS E2E issues v1.4).

## 작업 범위

- Python 백엔드 `app/*.py`, `vercel_wsgi.py`, `main.py`
- 프런트엔드 `web/app.js`, `web/share.js`와 연결된 HTML/CSS
- SQLite/PostgreSQL 쿼리 호환성, 세션 및 CSRF, 권한 분리
- Panta API 목록/상세 조회/시장 연결/가격 스냅샷 처리
- Vercel 및 Docker 설정과 Python 의존성
- 데이터 내보내기, 공개 공유 보고서, 초대 플로우

## 수정 내용

1. **PostgreSQL dict_row 버그:** `app/storage.py`의 Decision별 개수 조회에서 `row[0]`을 컬럼명으로 교체. `KeyError(0)`을 404로 잘못 처리하던 서버 경로도 500으로 변경.
2. **의존성 선언:** `pyproject.toml`에 `psycopg[binary]>=3.2,<4` 추가 (`requirements.txt`와 일치).
3. **팀 초대:** `/?invite=` 링크는 소개 페이지만 열었으므로 `/app?invite=`로 수정하고, 가입/로그인 직후 초대 수락 창을 표시.
4. **날짜 검증:** `2026-02-30`처럼 형식만 맞는 잘못된 날짜를 서버에서 거부.
5. **알림 임계치:** `nan`, `inf` 입력을 거부하여 JSON의 비정상 수치를 막음.
6. **시간대 표시:** 날짜 전용 값이 일부 시간대에서 하루 전날로 보이는 현상 수정.
7. **CSV 내보내기:** 사용자 입력이 `=`, `+`, `-`, `@`로 시작할 때 스프레드시트 수식 실행 방지.
8. **연결 오류 UI:** 세션을 확인할 수 없는 상태를 로그아웃 여부가 확인된 것처럼 표현하지 않음.
9. **릴리스 버전:** 서버 상태, 서버 헤더, pyproject 버전을 `1.5.0`으로 일치.

## 검증 내용

- Python 자동 테스트: 46개 통과 (기존 40개 + 신규 통합 테스트 6개).
- JavaScript 회귀 테스트: 3개 통과.
- `node --check web/app.js`, `node --check web/share.js` 통과.
- Python 문법 검사 통과.
- 프런트엔드의 data-act 30개와 이벤트 처리기 30개 매칭.
- WSGI API 테스트: 가입 → 세션 → Workspace → Decision → Forecast → 모의 Panta Market 연결 → 가격 저장 → 익명 공개 Report → 프로세스 재초기화 후 세션/DB 재확인.

## 아직 검증하지 못한 사항

- 실제 Neon PostgreSQL과 Panta Live API 서버 통신: 이 환경에 사용자의 새 비밀키와 데이터베이스 연결권한이 없음.
- Vercel 클라우드 최신 배포/브라우저 E2E 검증: 사용자의 GitHub Push 및 배포가 필요.
- Panta 실서버가 반환하는 시장 제목/YES/NO 가격: 누락된 데이터에 가상 가격을 넣지 않음.
- 제3자 보안 감사, 확장성/장애복구 및 상용 운영 수준의 최종 인증: 수행하지 않음.

**테스트 통과는 운영 서비스 전체 성공을 증명하지 않습니다.** 실제 서비스에서 E2E 테스트를 완료한 뒤에만 해커톤 제출 준비 완료로 판단하세요.

## macOS 적용 (기존 저장소 유지)

```bash
cd /path/to/your/outcomeos
git status --short
git pull --ff-only origin main
unzip -o "$HOME/Downloads/OutcomeOS-v1.5-FINAL-AUDIT-PATCH.zip" -d .
python3 -m unittest discover -s tests -q
node tests/test_client_regressions.cjs
node --check web/app.js
node --check web/share.js
git diff --check
git status --short
git add .gitignore app/http_api.py app/storage.py pyproject.toml web/app.js web/share.js \
  tests/test_full_audit.py tests/test_postgres_dictrow_compat.py \
  docs/FINAL_AUDIT_KO.md docs/AUDIT_REPORT_EN.md docs/POSTGRES_DICTROW_HOTFIX_KO.md
git diff --cached --name-status
git commit -m "Audit and stabilize OutcomeOS v1.5"
git push origin main
```

작업 트리에 사용자 수정 사항이 있다면, 먼저 별도 브랜치 또는 커밋으로 백업하세요. `git reset --hard`, `git push --force`는 사용하지 마세요. 서버 키는 Vercel 환경변수에만 보관해야 합니다.
