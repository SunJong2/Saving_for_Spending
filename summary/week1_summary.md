# 1주차 정리 — 기획 / DB 설계 / 프로젝트 세팅

## 0. 한 일 한눈에 보기

```
1. 기능 명세서 확정 (MVP / 추가 기능 구분)
2. DB 설계 (테이블 3개, 기본키/외래키 관계)
3. FastAPI 프로젝트 세팅 (가상환경, 파일 분리, Git)
```

---

## 1. 프로젝트 개요

**"소비를 위한 저축" 앱**
- 단기 구매 목표(예: 30만원 자켓)를 세우고, 참은 소비를 가상으로 적립해 목표를 달성하는 서비스
- 기존 저축(막연한 미래 대비)과 달리 **단기적·구체적 보상**을 동기로 삼는 것이 차별점
- 형태: 모바일 우선 반응형 웹 + PWA (배포/수정/분석이 유리한 웹으로 개발, 마지막에 홈 화면 추가 지원)

### 기능 명세

**MVP (필수)**
1. 회원가입 / 로그인
2. 목표 생성 — 이름, 목표 금액, 마감일 (선택: 상품 이미지)
3. 절약 기록 추가 — 금액, 카테고리, 메모(선택)
4. 목표 상세 — 저금통 UI, 진행률 %, 모인 금액/목표 금액
5. 목표 달성 처리

**추가 기능 (MVP 완성 후)**
6. 퀵 버튼 — 자주 쓰는 절약 항목 원터치 등록
7. Streak — 연속 절약 일수
8. 환산 표시 — "치킨 N마리 참음"
9. 달성 히스토리 — 완료한 목표들이 쌓이는 페이지

**정책 결정**
- 목표는 **한 번에 하나만** 진행 (컨셉에 부합: 하나에 집중해서 빨리 달성)
- 1차 버전 제외: 소셜 기능, 실계좌 연동, AI 코치 → README에 "향후 계획"으로

---

## 2. DB 설계

### 기본키 vs 외래키 (핵심 개념)

- **기본키(Primary Key)**: 그 테이블 안에서 각 행을 유일하게 구분하는 값. 중복 불가, NULL 불가. "내 신분증"
- **외래키(Foreign Key)**: **다른 테이블의 기본키를 가리키는** 값. "남의 신분증 번호를 적어둔 메모"

```
users (id=1)  ←──  goals.user_id = 1  ←──  savings.goal_id = 5
   기본키              외래키                     외래키
```

같은 숫자라도 역할이 다름: `users.id`는 자기 테이블의 기본키, `goals.user_id`는 그것을 가리키는 외래키.

### 테이블 구조

```
users
├── id            INTEGER  기본키, 자동증가
├── email         TEXT     UNIQUE (중복 가입 방지)
├── password_hash TEXT     원문 저장 금지 → 2주차에서 구현
├── nickname      TEXT
└── created_at    TEXT

goals
├── id             INTEGER  기본키
├── user_id        INTEGER  외래키 → users.id
├── name           TEXT     ("자켓")
├── target_amount  INTEGER  (300000)
├── current_amount INTEGER  DEFAULT 0
├── deadline       TEXT     (D-day, 페이스 계산용)
├── is_completed   BOOLEAN  DEFAULT 0
├── image_url      TEXT     NULL 허용
├── created_at     TEXT
└── completed_at   TEXT     달성 전엔 NULL

savings
├── id          INTEGER  기본키
├── user_id     INTEGER  외래키 → users.id
├── goal_id     INTEGER  외래키 → goals.id
├── category    TEXT     ("배달음식") — 통계/퀵버튼의 기반
├── amount      INTEGER  (20000)
├── memo        TEXT     NULL 허용
├── image_url   TEXT     NULL 허용
└── created_at  TEXT     시분초까지 저장
```

### 설계하면서 배운 판단 기준

- **`is_completed` 하나로 두 기능 해결**: "한 번에 목표 하나" 제한(미완료 목표 존재 시 생성 거부) + 달성 히스토리(완료된 것만 조회)
- **`goal_id`가 필요한 이유**: 목표가 여러 개 쌓이면(달성 후 새 목표) 각 절약 기록이 어느 목표 소속인지 알아야 함. "지금은 하나"여도 데이터는 누적됨
- **`category`를 자유 텍스트(name)와 분리한 이유**: "치킨"/"chicken"/"BHC"를 묶어서 집계할 수 없음. 통계·퀵버튼은 카테고리 기반
- **시간은 시분초까지 저장**: 하루에 여러 기록 시 정렬 필요. 화면에는 날짜만 잘라서 표시
- **`created_at`은 거의 모든 테이블에 습관처럼**: 정렬, 디버깅에 사용

### SQL 제약조건 (database.py에서 사용)

| 문법 | 의미 |
|------|------|
| `PRIMARY KEY AUTOINCREMENT` | 기본키, 1부터 자동 증가 |
| `UNIQUE` | 같은 값 중복 저장 거부 (이메일) |
| `NOT NULL` | 빈 값 금지. NULL 허용할 컬럼(memo 등)엔 안 붙임 |
| `DEFAULT 0` | 값을 안 주면 자동으로 0 |
| `FOREIGN KEY (x) REFERENCES t(id)` | 외래키 공식 선언 |

---

## 3. 프로젝트 세팅

### 가상환경 (venv)

```bash
python3 -m venv venv          # 만들기 (프로젝트당 1회)
source venv/bin/activate      # 켜기 (작업 시작할 때마다)
```

- 프로젝트별로 독립된 파이썬 환경 → 라이브러리 버전 충돌 방지
- 켜져 있으면 프롬프트에 `(venv)` 표시, `pip`/`python`으로 명령 가능 (3 안 붙여도 됨)
- 프롬프트의 `git:(main)`은 "이 폴더는 Git 저장소, main 브랜치"라는 **정보 표시**일 뿐. 갇힌 상태 아님

### 파일 구조 (역할별 분리)

```
SavingApp/
├── venv/           가상환경 (Git에 안 올림)
├── main.py         서버 시작점 (init_db 호출, 라우터 등록)
├── database.py     DB 연결(get_connection) + 테이블 생성(init_db)
├── auth.py         (2주차) 회원가입/로그인
└── static/         (예정) 프론트엔드
```

- 날씨 앱은 main.py 하나였지만, 규모가 커지면 역할별 분리가 필수
- `from database import init_db` — 다른 파일의 함수를 가져와 연결

### .gitignore

```
venv/           수십MB, 각자 pip install로 재생성하는 것
__pycache__/    파이썬 자동 생성 캐시
saving.db       사용자 데이터(이메일, 비번 해시) — 공개 금지
.DS_Store       맥 시스템 파일
```

- `.gitignore` 자체는 올라가는 게 정상 (팀원과 규칙 공유)
- **이미 추적된 파일은 .gitignore에 적어도 계속 따라옴** → `git rm --cached 파일` (또는 `-r` 폴더)로 추적 해제 후 commit/push
- `--cached`: Git 추적에서만 제거, 실제 파일은 유지. 안 붙이면 파일이 진짜 삭제됨

### requirements.txt

```bash
pip freeze > requirements.txt              # 설치 목록 저장
pip install -r requirements.txt            # 다른 환경에서 복원
```

- venv를 안 올리는 대신 "뭘 설치해야 하는지"를 공유하는 파일

### Git 습관

- **add(rm) → commit → push 는 세트.** 하나라도 빠지면 GitHub에 반영 안 됨
- `git status` — 커밋 전 변경사항 확인
- `cat 파일명` — 디스크에 실제 저장된 내용 확인 (편집기 표시 ≠ 저장 완료)

---

## 4. 8주 플랜에서의 위치

| 주차 | 내용 | 상태 |
|------|------|------|
| 1주 | 명세 + DB 설계 + 세팅 | ✅ |
| 2주 | 회원가입/로그인 (JWT) | ✅ |
| 3~4주 | 핵심 CRUD (목표/절약 기록) | ← 다음 |
| 5주 | 통계 API + 프론트 기본 화면 |  |
| 6주 | 저금통 UI, 디자인 |  |
| 7주 | 배포 + 버그 수정 |  |
| 8주 | README, 시연 GIF, 회고 |  |

## 5. 면접 셀프 체크

- 기본키와 외래키의 차이는? 외래키가 왜 필요한가?
- 테이블 간 1:N 관계를 어떻게 표현하는가? (user 1명 : goal 여러 개)
- 가상환경은 왜 쓰는가?
- venv와 DB 파일을 Git에 올리면 안 되는 이유는?
- requirements.txt의 역할은?
- MVP를 먼저 정의하고 기능을 단계적으로 확장하는 이유는?
