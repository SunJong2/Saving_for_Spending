# 7주차 정리 — 배포 / PostgreSQL 전환 / 폰 UI 수정

이번 주차의 핵심: **로컬에서만 돌던 앱을 실제 인터넷 서비스로 만들었고, 그 과정에서 배포 환경에서만 드러나는 문제들(동시성, 시간대, 중복 제출)을 직접 만나 해결했다.** 로컬 개발로는 절대 못 겪는 경험.

## 0. 만든 것 한눈에 보기

```
[배포]
Render 배포 (moasa.onrender.com)      서버 배포 + 자동 재배포(push 감지)
루트 URL 리다이렉트                    / → /static/login.html

[DB 전환]
SQLite → PostgreSQL (Supabase)         database is locked 문제 해결
with 컨텍스트 매니저                    연결 자동 정리 (try/finally)

[폰 UI 수정]
스크롤/잘림, 날짜 입력칸, UTC→KST, 중복 제출 방지
```

---

## 1. 앱 이름 확정: 모아사 (moasa)

- "모아서 사는 재미" — 수단(모으다) + 목적(사다)을 세 글자로 압축
- 처음 아이디어 '아껴야 산다'에서 훈계 톤(아껴야)을 빼고 행동(모아서)으로 다듬은 것
- 이름 짓기 기준: 짧고(2~4음절), 명사형, 앱의 감정을 담고, 부르기 쉬울 것
- 슬로건 "모아서 사는 재미", 기능 화면 문구는 재치 담당("뭐 사지?" 등)
- **이름 결정 원칙**: 오래 고민한다고 더 좋아지지 않음. 입에 붙는지가 핵심 기준

---

## 2. 배포 (Render)

### 배포 준비
- `runtime.txt`: python-3.12.7 (로컬 3.14지만 라이브러리 호환성 위해 배포는 안정 버전. 우리 코드는 표준 문법뿐이라 리스크 낮음)
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - `--host 0.0.0.0`: 외부 접속 허용 (기본 127.0.0.1은 자기 컴퓨터만)
  - `--port $PORT`: Render가 지정한 포트 사용 (환경변수로 받음)
  - `--reload` 제거: 개발 전용이라 배포엔 해로움
- 환경변수는 Render 대시보드에 등록 (.env 대신). SECRET_KEY, DATABASE_URL
- `pip freeze > requirements.txt`로 의존성 최신화

### 배포 자동화 (CI/CD 기본형)
- GitHub에 push → Render가 감지 → 자동 재배포
- 로컬 수정 → push → 몇 분 뒤 실서비스 반영

### 개발/배포 환경 분리 원칙
- **개발은 로컬에서, 배포는 검증된 것만.** 매번 push해서 배포로 테스트하면 커밋 지저분·느림·미검증 코드 배포
- 흐름: 코드 수정 → 로컬 테스트(커밋 안 함) → 다 되면 커밋+push
- 폰 UI 테스트: 같은 와이파이면 `http://맥IP:8000`으로 폰에서 로컬 서버 접속 가능
  - client isolation 있는 공용 와이파이는 안 됨 → 반응형 디자인 모드로 폴백

---

## 3. SQLite → PostgreSQL 전환 (이번 주 최대 작업)

### 왜 전환했나 (README 핵심 스토리)
- Render 무료 티어는 서버가 잠들었다 깨면 파일시스템 초기화 → SQLite 파일(saving.db)의 데이터가 날아감
- 게다가 배포 후 **database is locked** 발생: SQLite는 쓰기 시 파일 전체를 잠금(한 번에 하나의 쓰기만). 동시 요청이 겹치면 충돌
- 로컬에선 순차 요청이라 안 겪었지만, 배포에선 드러남
- **"SQLite는 실서비스에 안 쓴다"를 책이 아니라 몸으로 배움**

### 무료 영구 구성
```
서버  Render 무료 (콜드 스타트 있음, 첫 접속 30초~1분)
DB    Supabase PostgreSQL 무료 (기한 없음, 1주 미사용 시 일시정지—데이터는 보존)
```
- Render 무료 PostgreSQL은 90일 만료라 Supabase 선택
- 콜드 스타트는 README에 명시하면 오히려 인프라 이해 신호. 면접 전 미리 깨워두면 됨

### Supabase 세팅
- 연결 문자열(DATABASE_URL): pooler 방식 사용 (IPv4 지원, Render 무료 티어가 IPv4라 direct connection은 안 됨)
- 형식: `postgresql://유저:비밀번호@호스트:포트/db` — 비밀번호에 특수문자 있으면 URL 파싱 깨짐 → token_hex로 생성 권장
- RLS "UNRESTRICTED" 경고는 무시 OK: 우리는 백엔드 서버 경유 구조라 접근 제어가 애플리케이션 레이어(JWT+user_id 조건)에 있음. RLS는 프론트가 DB에 직접 붙을 때 필요
- 로컬·배포가 같은 Supabase DB를 봄 → 로컬에서 만든 계정으로 배포에서도 로그인됨

### 코드 전환 (database.py + 백엔드 3파일)
```python
# database.py — 컨텍스트 매니저
import psycopg
from contextlib import contextmanager

@contextmanager
def get_db():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()   # 예외·return 무관하게 반드시 닫힘
```

**전환 규칙 (SQLite → PostgreSQL):**
- `get_connection()` + 수동 `conn.close()` → `with get_db() as conn:` (close 전부 삭제)
- 플레이스홀더 `?` → `%s`
- 불리언 `= 0/1` → `= FALSE/TRUE`, `INTEGER PK AUTOINCREMENT` → `SERIAL PRIMARY KEY`
- 파이썬 비교 `goal[0] == 1` → `if goal[0]:` / `== False` → `if not goal[0]:` (PEP 8: == True/False 안 씀)

### with (컨텍스트 매니저)가 정석인 이유
- 수동 close는 **예외가 나면 실행 안 됨** → 연결이 안 닫힌 채 잠금이 남음 (database is locked의 근본 원인)
- `with open()`처럼 파이썬에서 "열면 닫아야 하는 것"은 전부 with가 표준. try/finally의 finally가 무조건 정리 보장
- 학습 초기엔 수동 close로 흐름을 눈에 보이게 했고, 이해한 뒤 정석 도구로 이동

---

## 4. 폰 UI 문제 수정

### 스크롤 안 됨 / 콘텐츠 잘림 (#1, #5)
- 원인 1: `class="container has tabbar"` 오타 — `has-tabbar`가 하이픈 하나의 클래스인데 공백으로 띄어 두 개로 인식 → padding-bottom 미적용
- 원인 2: `.container`의 `min-height:100vh` + `display:flex; flex-direction:column` 조합이 콘텐츠 넘쳐도 스크롤 막음
- 해결: container에서 flex 두 줄 제거 (div는 기본이 세로 쌓기라 불필요), has-tabbar 오타 수정
- **왜 로그인/목표생성은 됐나**: 콘텐츠가 화면보다 작아 스크롤이 필요 없었을 뿐. 홈은 기록 쌓이면 넘침
- **왜 히스토리는 됐나**: 콘텐츠를 모달에 넣고 모달에 자체 `overflow-y:auto`를 줬어서 container 문제와 무관했음

### iOS date input (#2)
- iOS는 date input을 자기 방식으로 그림(회색 배경, 파란 글씨, 가운데 정렬, 고정 너비로 삐져나옴)
- `-webkit-appearance:none; appearance:none`로 기본 스타일 제거 → 삐져나옴 해결
- 색은 `color`로, 정렬은 `::-webkit-date-and-time-value { text-align:left }` (일반 text-align은 date 내부에 안 먹음. 가상 요소로 내부 값 컨테이너를 직접 지정)
- **빈 값일 때 텅 비어 보임**: date는 placeholder 속성이 안 먹음 → 라벨을 칸 위에 붙임(.field-label). 라벨은 date UX 정석

### 폼 라벨 판단 (통일성의 단위)
- add-goal/edit-goal 세 칸에 라벨 추가, **로그인/가입은 placeholder 유지**
- 원칙: "앱 전체가 똑같아야 한다"가 아니라 "같은 맥락 안에서 똑같아야 한다". 로그인은 빠른 입력, 목표 생성은 신중한 입력 → 성격이 달라 달라도 됨
- placeholder도 맥락별로: add-goal은 예시("예: 에어팟 프로"), edit-goal은 이름칸 비움(수정 맥락엔 예시가 뜬금없음). "숫자만 입력"은 형식 안내라 양쪽 유지
- 라벨 = 항상 보이는 항목명, placeholder = 예시/형식 힌트로 역할 분담

### UTC → KST (#6)
- Render 서버는 UTC라 `datetime.now()`가 한국보다 9시간 느림 (로컬은 한국시간이라 안 보였음)
- database.py에 `KST = timezone(timedelta(hours=9))` 정의, 각 파일서 import
- 저장용(created_at, completed_at): `datetime.now(KST)`
- 비교/d_day용: `datetime.now(KST).date()`
- **함정**: naive datetime(strptime 결과)과 aware datetime(now(KST)) 직접 비교 시 TypeError. 마감일 검증은 `deadline_date.date() <= datetime.now(KST).date()`로 양쪽 date 통일
- **login의 JWT 만료는 UTC 유지** — 절대 시점이라 UTC가 표준. 여기까지 KST로 바꾸면 안 됨

### 중복 제출 방지 (#7, #8, #9)
- 증상: 버튼 빠르게 연타 → 기록 3~5개 중복 저장
- **원인은 프론트**: 연타로 함수가 여러 번 호출됨. SQLite lock이 "우연히" 막던 걸 PostgreSQL이 정상 처리하며 드러남 (lock은 기능이 아니라 부작용이었음). 로컬에서도 재현됨 — 원래 있던 문제
- 해결: 잠금 깃발 + try/finally
```javascript
let isAddingSaving = false;   // 함수 밖 (여러 클릭이 공유)
async function add_saving() {
    if (isAddingSaving) return;
    isAddingSaving = true;
    try { /* 검증+fetch 전부 */ } finally { isAddingSaving = false; }
}
```
- **적용 기준**: "서버 상태를 바꾸는(쓰기) + 중복 시 부작용" → 잠금 필요. 조회(GET)는 불필요
- 대상: add-saving, add-goal, edit-goal, deleteGoal, deleteCompletedGoal, deleteSaving
- 삭제류는 변수 각각 분리(한 화면에 삭제 여럿이면 서로 간섭 방지)
- **기록 삭제가 특히 위험**: 중복 실행 시 current_amount 이중 차감 가능
- finally를 성공 경로에도 넣는 이유: 페이지 이동(location.href) 시엔 무의미하지만, **실패 경로(res.ok=false)에선 페이지가 안 떠나므로 잠금 해제 필수**. 없으면 한 번 실패 후 버튼 영구 잠김
- **프론트 잠금은 우회 가능** → 완전한 방어는 백엔드 멱등성(idempotency). 지금은 프론트로 충분, 나중 주제

### 완료된 완료 목표 삭제 API (설계 판단)
- `DELETE /goals/{goal_id}` 신설 (기존 `/goals/current`는 진행 중 목표만 삭제 가능했음)
- **A안(별도 엔드포인트) vs B안(통합)**: A 선택. 이유는 두 삭제의 의미가 다름 — 진행 중 삭제="도전 포기", 완료 삭제="기록 지우기". UX 문구도 다름("기록도 사라져요" vs "달성 기록이 사라져요")
- IDOR 방어 재적용(소유권 검사), 완료 여부 검증(미완료면 400 — 사용자 안 보는 개발자용 문구)

---

## 5. 현재 상태 / 다음

```
✅ 배포 완성 (Render + Supabase, 데이터 영구 보존)
✅ 기능 버그 전부 해결 (스크롤, 날짜칸, UTC, 중복제출)
⬜ 홈 레이아웃 다듬기 (다음) — 이모지→아이콘, 저금통 개선, 미관 잔여(#3,#4), CSS 리팩토링, favicon
⬜ 부가 기능 택1~2 (퀵버튼/streak/통계/환산)
⬜ PWA (manifest.json)
⬜ 데모 계정 + README
```

## 6. 면접 셀프 체크

- SQLite에서 PostgreSQL로 옮긴 이유는? (database is locked = 동시성/파일 잠금)
- with(컨텍스트 매니저)를 쓰는 이유는? 수동 close의 문제는? (예외 시 미실행)
- Supabase RLS를 안 켜도 되는 이유는? (백엔드 경유 구조, 접근제어가 앱 레이어에)
- 서버 시간대 문제(UTC/KST)를 어떻게 처리했나? naive/aware datetime 차이는?
- 중복 제출의 원인과 방어는? 프론트 잠금의 한계는? (우회 가능 → 백엔드 멱등성)
- 배포 자동화(push→재배포)는 어떻게 동작하나?
- 개발 환경과 배포 환경을 분리하는 이유는?
