# OutcomeOS — PostgreSQL dict_row HTTP 404 수정

## 확인한 오류

Work 브라우저가 보고한 `0 (HTTP 404)`는 로그인 후 Workspace 상세 조회에서 발생할 수 있는 코드 오류와 정확히 일치합니다.

PostgreSQL 연결은 `psycopg.rows.dict_row`를 사용합니다. 기존 `app/storage.py`의 `overview()`에서 `COUNT(*)` 결과에 `fetchone()[0]`을 사용했는데, dict_row에는 정수 인덱스가 없으므로 `KeyError(0)`이 발생합니다. `app/http_api.py`가 `LookupError`를 HTTP 404로 변환하고 `KeyError`도 `LookupError`의 하위 클래스이므로 응답에 `{"error":"0"}`이 나타납니다.

## 수정 내역

- `app/storage.py`: `COUNT(*) AS total`과 `fetchone()['total']`을 사용하여 SQLite/PostgreSQL 양쪽에서 동작하게 수정.
- `app/http_api.py`: 프로그래밍 실수로 발생한 `KeyError`는 HTTP 404가 아닌 내부 오류(500)로 응답하고 상세 내용은 서버 로그에만 기록.
- `tests/test_postgres_dictrow_compat.py`: dict 형태의 DB 결과로 빈 Workspace, Decision 생성, 카운트, WSGI 회원가입→Decision 생성→Workspace 조회→세션 확인과 오류 분류를 검사.

## macOS 적용 순서

```bash
# 이미 GitHub 저장소가 있는 outcomeos 폴더에서 실행
pwd
git status
git pull --ff-only origin main

# Finder에서 다운로드한 ZIP을 더블 클릭해 압축을 풉니다.
# 압축을 푼 폴더의 전체 경로를 아래에 사용하세요.
cp -R "$HOME/Downloads/OutcomeOS-Postgres-404-HOTFIX/app/." ./app/
cp -R "$HOME/Downloads/OutcomeOS-Postgres-404-HOTFIX/tests/." ./tests/
cp -R "$HOME/Downloads/OutcomeOS-Postgres-404-HOTFIX/docs/." ./docs/

python3 -m unittest discover -s tests -q
node tests/test_client_regressions.cjs

git add app/storage.py app/http_api.py tests/test_postgres_dictrow_compat.py docs/POSTGRES_DICTROW_HOTFIX_KO.md
git diff --cached --check
git diff --cached --name-status
git commit -m "Fix PostgreSQL dict row workspace 404"
git push origin main
```

이미 커밋되지 않은 변경 사항이 있다면 `git pull`/복사/커밋 전에 `git status`를 확인하고 병합 충돌이 없는지 점검하세요. `git push --force`는 사용하지 마세요.

## 배포 후 기대 동작

1. Vercel Production의 최신 Commit이 `Ready`인지 확인
2. `/api/health`가 정상적으로 응답하는지 확인
3. 앱에서 새로고침 후 로그인 유지 여부 확인
4. Decision Room 생성 후 목록, `Link →` 선택 여부 확인
5. 브라우저 개발자 도구(Network)에서 `/api/auth/me`, `/api/workspaces`, `/api/workspaces/<ID>` 응답 상태 확인

`0 (HTTP 404)`가 사라졌더라도 네트워크/세션 유지와 실제 Panta 데이터는 별도 재검증해야 합니다. API 키·비밀번호·쿠키 값은 공유하지 마세요.
