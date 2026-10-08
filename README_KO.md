# OutcomeOS v1.3 — Panta 기반 예측시장 의사결정 서비스

기존 단순 로컬 데모를 넘어, **실제 사용자 계정/팀/결정/예측/근거/Panta 실시간 시세/공유 보고서**가 있는 애플리케이션입니다. Panta는 **읽기 전용**으로 사용하며, 거래·자금 보관은 하지 않습니다.

## 공개 배포: VPS/도메인 비용 $0 가능

**[`docs/DEPLOY_FREE_KO.md`](docs/DEPLOY_FREE_KO.md)** 를 순서대로 따라하세요.

- **Render 무료 웹서버**: HTTPS 주소 자동 생성 (`.onrender.com`)
- **Neon 무료 PostgreSQL**: Render 재시작 뒤에도 사용자 기록을 안전하게 보관
- **Panta Live API**: 실제 Panta 예측시장과 YES/NO 가격 조회

Render의 `render.yaml`이 배포 설정을 구성합니다. **Neon DATABASE_URL과 새 Panta API 키는 Render 비밀 환경변수에만 입력**합니다. 채팅에서 노출된 기존 Panta 라이브 키는 먼저 폐기하세요.

## 로컬 실행

Python 3.10+ 설치 후 압축 해제된 프로젝트 폴더에서:

```powershell
python main.py
```

- 소개 페이지: `http://127.0.0.1:8766/`
- 앱: `http://127.0.0.1:8766/app`

로컬 모드 SQLite는 표준 라이브러리만 사용합니다. Render 무료 서버는 SQLite 데이터가 소실될 수 있으므로 `DATABASE_URL` 없는 배포를 차단합니다.

## 제출에 필요한 자료

1. 실제 공개 Render HTTPS 사이트 URL
2. GitHub 저장소 URL(비밀 키 없는 소스코드)
3. **2~3분 발표 영상** 및 **최대 3분 실제 제품 데모 영상**
4. 영어 제품 설명과 Panta 연동 근거
5. **Colosseum**와 **Superteam Panta Sidetrack**에 각각 제출

영어 제출 문구: [`docs/SUBMISSION_EN.md`](docs/SUBMISSION_EN.md)  
영어 영상 스크립트: [`docs/VIDEOS_EN.md`](docs/VIDEOS_EN.md)  
한국어 무료 배포 가이드: [`docs/DEPLOY_FREE_KO.md`](docs/DEPLOY_FREE_KO.md)

**해커톤 공식 제출 마감: 2026년 10월 12일.** 프로젝트 코드만 완성됐다고 공식 제출이 자동 완료되는 것은 아닙니다. 실제 API/Neon 서버 및 브라우저 접속까지 확인하고 URL과 영상 링크를 사용자가 직접 등록해야 합니다.

## 코드 검증

```powershell
python -m unittest discover -s tests -v
```

자동 테스트는 로컬 흐름과 PostgreSQL 연결 변환 규격을 검사합니다. 실제 Neon/Panta 서버 호출은 사용자 계정과 새 비밀 키가 필요한 별도 배포 확인 절차입니다. Render 무료 서비스는 일정 시간 비활성 시 잠들 수 있으며 기업용 상용 안정성 보장은 없습니다.
