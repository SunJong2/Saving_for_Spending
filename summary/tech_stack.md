# SavingApp 기술 스택 정리

"소비를 위한 저축" 앱에서 사용 중이거나 사용 확정된 기술들.
(미확정 항목 — 통계 GROUP BY 심화, PWA 적용 범위 등 — 은 제외)

---

## 1. 백엔드

### Python 3 + FastAPI
- 역할: 웹 프레임워크. API 서버의 뼈대
- 사용 중인 기능:
  - `APIRouter` — 기능별 파일 분리 (auth / goals / savings)
  - Pydantic `BaseModel` — 요청 본문(JSON) 형식 정의·자동 검증 (XxxCreate/XxxUpdate 분리 패턴)
  - `Depends` — 의존성 주입. get_current_user를 모든 보호 API의 문지기로
  - `HTTPException` — 상태 코드 기반 에러 응답 (400/401/404/409 구분)
  - 경로 매개변수 (`/goals/{goal_id}/savings`), 자동 문서 (/docs, Swagger UI)
  - `StaticFiles` — 프론트 정적 파일 서빙

### Uvicorn
- 역할: ASGI 서버. FastAPI 앱을 실제로 구동 (`--reload`로 개발 중 자동 재시작)

### SQLite (sqlite3 — 파이썬 내장)
- 역할: 데이터베이스. 파일 하나(saving.db)짜리 관계형 DB
- 테이블: users / goals / savings (외래키로 1:N 관계)
- 사용 중인 SQL: SELECT/INSERT/UPDATE/DELETE, WHERE, ORDER BY, LIMIT,
  COALESCE(부분 수정), UNIQUE/NOT NULL/DEFAULT/FOREIGN KEY 제약, AUTOINCREMENT
- 트랜잭션: commit 시점 일괄 확정으로 다중 쿼리 정합성 유지
- 향후: 배포 시 PostgreSQL 전환 검토 (초기 계획)

### passlib[bcrypt] (bcrypt 4.0.1 고정)
- 역할: 비밀번호 해시. 솔트 자동 생성·포함, 의도적으로 느린 해시로 무차별 대입 방어
- 원문 비밀번호는 어디에도 저장하지 않음

### python-jose[cryptography]
- 역할: JWT 발급(encode)·검증(decode)
- HS256 서명, 페이로드에 user_id + exp(만료 60분)
- 무상태 인증: 서버는 비밀키 하나만 보유, 토큰 저장 없이 서명 재계산으로 검증

### python-dotenv
- 역할: .env 파일의 환경변수 로드 (SECRET_KEY 분리)
- .env는 .gitignore로 보호, 키 생성은 secrets.token_hex(32)

---

## 2. 프론트엔드

### HTML / CSS (vanilla)
- 프레임워크 없이 순수 구현 (React는 앱 완성 후 확장 학습 과제)
- 디자인 시스템: CSS `:root` 변수로 색·라운드 통일 (토스풍 미니멀 + 그라데이션 포인트)
- 모바일 우선: max-width 480px 컨테이너, viewport 메타 태그
- 페이지: login / signup / index(홈) + 예정: add-goal, add-saving, history

### JavaScript (vanilla)
- `fetch` — API 호출 (GET/POST, JSON body, Authorization: Bearer 헤더)
- `localStorage` — JWT 토큰 보관 (도메인 단위, 브라우저 재시작에도 유지)
- 진입 가드 패턴 — 페이지 로드 시 토큰 유무(1차) + API 401 응답(2차)으로 미인증 접근 차단
- DOM 조작 — getElementById, textContent, innerHTML, style.display 분기 렌더링
- `addEventListener` — 엔터 로그인 등 이벤트 처리
- `URLSearchParams` — 쿼리 파라미터(?expired=1)로 페이지 간 상태 전달
- 템플릿 문자열(백틱), 리스트 렌더링(map + join), toLocaleString(금액 표기)
- 프론트 입력 검증 — 빈 값, 이메일 형식(@), 비밀번호 재확인 (입력 편의 계층)

---

## 3. 개발 도구·환경

### Git / GitHub
- 버전 관리 + 원격 저장소 (포트폴리오 겸용)
- .gitignore로 venv, __pycache__, saving.db, .env 제외
- add → commit → push 세트, 의미 있는 커밋 메시지

### venv + requirements.txt
- 프로젝트 독립 가상환경, pip freeze로 의존성 목록 공유

### VSCode + 터미널
- 개발 환경. sqlite3 CLI로 DB 직접 조사·정리 (디버깅 도구로 활용)

### 브라우저 개발자 도구 (Safari)
- 콘솔(JS 에러), 네트워크(요청/응답, 캐시 비활성화), 저장 공간(localStorage), 요소(실제 DOM)
- 프론트 디버깅 표준 루틴: 상태 초기화 → 재현 경로 통제 → 관찰

### FastAPI /docs (Swagger UI)
- 백엔드 단독 테스트 도구 (프론트 없이 API 검증)

---

## 4. 앞으로 사용 확정

### Render (배포)
- 무료 티어로 서버 배포 → 실제 URL 확보 (7주차 예정)
- 이때 함께: 환경변수를 Render 대시보드에 등록, DB 전략 결정

### PWA (manifest.json)
- 홈 화면 추가 시 앱처럼 실행되는 웹 (마지막 주 예정)
- "모바일 사용성이 핵심이라 모바일 우선 웹 + PWA 선택"이라는 의사결정 스토리

### 통계 API (프론트 필요 시점에 설계)
- SQL GROUP BY 집계 (카테고리별 비중, 주간/월간 합계, streak)
- 화면을 먼저 그려 필요한 데이터를 확정한 뒤 설계하는 순서로 진행

---

## 5. 자소서/이력서 한 줄 요약용

```
Backend  : Python, FastAPI, SQLite, JWT(python-jose), bcrypt(passlib), python-dotenv
Frontend : HTML/CSS/JavaScript (vanilla), 모바일 우선 반응형, PWA(예정)
Infra    : Git/GitHub, venv, Render 배포(예정)
특징     : JWT 무상태 인증, IDOR 방어(소유권 검사), 입력 검증 이중화(프론트+백엔드),
           트랜잭션 기반 정합성, RESTful API 설계(메서드·상태 코드 의미 구분)
```
