# OutcomeOS — 신용카드 없이 Vercel 배포

이 문서는 기존 장시간 실행 HTTP 서버를 서버리스 WSGI 함수로 연결한 버전입니다.

## 준비

- GitHub OutcomeOS 저장소
- Neon PostgreSQL 연결 문자열 (비밀번호를 공개하지 마세요)
- Panta에서 새로 발급한 LIVE API 키 (기존에 노출된 키는 폐기)
- Vercel의 Hobby 계정 (개인 비상업적 데모에 한함; 해커톤 수상 가능성이 허용되는지는 규정 확인 필요)

## 1. 코드 교체 및 푸시

이 압축파일을 풀고 현재 `outcomeos` GitHub 저장소의 로컬 프로젝트 내용을 업데이트하세요.

```bash
# 현재 OutcomeOS Git 저장소에서 코드 파일을 업데이트한 다음
git add .
git commit -m "Add Vercel WSGI deployment"
git push origin main
```

> 기존 Git 저장소에 소스코드를 복사할 때 `.git` 디렉터리는 건드리지 마세요. `DATABASE_URL`, `PANTA_API_KEY`, `.env`를 커밋하지 마세요.

## 2. Vercel 배포

1. https://vercel.com/new 접속하여 GitHub로 로그인합니다.
2. `kakerumatsumoto756-debug/outcomeos` 저장소를 `Import`합니다.
3. 개인 Hobby 플랜과 **Other** 프레임워크(자동 감지 시 Python)를 사용합니다.
4. Project root는 리포지토리 루트입니다.
5. `DATABASE_URL`, `PANTA_API_KEY`를 환경변수로 추가합니다. 비밀정보를 공개하지 마세요.
6. 필요 시 `OUTCOMEOS_REQUIRE_POSTGRES=1`, `OUTCOMEOS_COOKIE_SECURE=1`, `OUTCOMEOS_SEED_EXAMPLES=0`을 추가합니다. 서버에서도 VERCEL 환경변수로 강제 설정합니다.
7. **Deploy**를 누릅니다. 실패하면 빌드 로그를 확인합니다.

## 3. 배포 검증

- `https://<your-project>.vercel.app/` — 공개 소개 페이지
- `https://<your-project>.vercel.app/api/health` — HTTP 200 및 JSON 상태
- `/app` — 회원가입, 로그인, 결정 생성, 팀 예측, 시장 조회
- 실제 Panta 연결은 Live 키로 검색 결과를 확인하고, 정상 시장의 가격을 조회해야 검증 완료

## 중요

- 이 WSGI 브리지는 로컬 동작을 검증했으나, **Vercel 실제 서버 배포와 Neon/Panta 실서버 호출은 아직 확인되지 않았습니다.**
- Vercel Hobby는 비상업적 개인 사용만 허용하므로, 해커톤 상금과 관련된 허용 여부는 Vercel에 확인해야 합니다.
- 서버리스에서는 인스턴스 메모리 기반 인증 시도 제한이 전체 인스턴스에 걸쳐 공유되지 않습니다. 공개 운영 전 외부 rate limiting 등을 추가하세요.
- 기존 데이터는 Neon에만 저장해야 합니다. Vercel의 임시 로컬 저장소를 사용하면 데이터가 사라집니다.
