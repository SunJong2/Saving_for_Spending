from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from database import get_connection
from auth import get_current_user

router = APIRouter()


class GoalCreate(BaseModel):
    name: str
    target_amount: int
    deadline: str          # "2026-08-15" 형식
    image_url: str | None = None   # 선택 항목 (안 보내면 None)


@router.post("/goals")
def create_goal(req: GoalCreate, user_id: int = Depends(get_current_user)):
    # 0. 입력 검증 — DB 건드리기 전, 함수 맨 앞에서
    #   마감일, 금액 형식 검증
    try:
        deadline_date = datetime.strptime(req.deadline, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")
    if deadline_date <= datetime.now():
        raise HTTPException(status_code=400, detail="마감일은 오늘 이후여야 합니다")
    if req.target_amount <= 0:
        raise HTTPException(status_code=400, detail="금액 설정이 올바르지 않습니다")


    conn = get_connection()
    cursor = conn.cursor()

    # 1. 미완료 목표가 있는지 검사 → 있으면 409 에러
    #    (힌트: conn.close() 잊지 말기)
    cursor.execute("SELECT id FROM goals WHERE user_id = ? AND is_completed = 0", (user_id,))
    if cursor.fetchone() is not None:
        conn.close()
        raise HTTPException(status_code= 409, detail= "이미 등록된 미완료 목표가 있습니다")

    # 2. INSERT (created_at은 datetime.now()... 패턴, 2주차 signup 참고)
    cursor.execute(
        "INSERT INTO goals (user_id, name, target_amount, deadline, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, req.name, req.target_amount, req.deadline, req.image_url, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    # 3. commit, close
    conn.commit()
    conn.close()
    return {"message": "goal created"}

@router.get("/goals/current")
def get_current_goal(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id, name, target_amount, current_amount, deadline, image_url
           FROM goals WHERE user_id = ? AND is_completed = 0""",
        (user_id,)
    )
    goal = cursor.fetchone()
    conn.close()

    if goal is None:
        raise HTTPException(status_code=404, detail="진행 중인 목표가 없습니다")

    goal_id, name, target_amount, current_amount, deadline, image_url = goal

    # 서버에서 계산해서 얹어주는 값들
    progress = round(current_amount / target_amount * 100, 1)
    d_day = (datetime.strptime(deadline, "%Y-%m-%d") - datetime.now()).days

    return {
        "id": goal_id,
        "name": name,
        "target_amount": target_amount,
        "current_amount": current_amount,
        "progress": progress,        # 진행률 %
        "d_day": d_day,              # 마감까지 남은 일수
        "deadline": deadline,
        "image_url": image_url,
    }

class GoalUpdate(BaseModel):
    name: str | None = None
    target_amount: int | None = None
    deadline: str | None = None
    image_url: str | None = None

@router.patch("/goals/current")
def update_goal(req: GoalUpdate, user_id: int = Depends(get_current_user)):
    # 0. 입력 검증 — 부분 수정이므로 deadline이 "왔을 때만" 검사
    #    (None = 안 보냄 = 기존 값 유지이므로 검증 대상 아님)
    if req.deadline is not None:
        try:
            deadline_date = datetime.strptime(req.deadline, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")
        if deadline_date <= datetime.now():
            raise HTTPException(status_code=400, detail="마감일은 오늘 이후여야 합니다")
        
    if req.target_amount is not None and req.target_amount <= 0:
        raise HTTPException(status_code=400, detail="금액 설정이 올바르지 않습니다")
    
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 수정 대상 = 이 사용자의 진행 중인 목표 (검사 먼저, goal[0] 사용은 그 다음!)
    cursor.execute(
        "SELECT id, current_amount FROM goals WHERE user_id = ? AND is_completed = 0",
        (user_id,)
    )
    goal = cursor.fetchone()
    if goal is None:
        conn.close()
        raise HTTPException(status_code=404, detail="진행 중인 목표가 없습니다")

    goal_id, current_amount = goal

    # 이미 모은 금액보다 낮게는 설정 불가 (설정 즉시 달성되는 애매한 상태 방지)
    if req.target_amount is not None and req.target_amount <= current_amount:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail= f"이미 {current_amount:,}원을 모았어요. 목표 금액은 그보다 커야 합니다"
        )

    # 2. 부분 수정: COALESCE(?, 컬럼) → 보낸 값(None 아님)은 새 값으로,
    #    안 보낸 값(None→NULL)은 자기 자신으로 갱신 = 기존 값 유지
    cursor.execute(
        """UPDATE goals SET name = COALESCE(?, name),
        target_amount = COALESCE(?, target_amount),
        deadline = COALESCE(?, deadline),
        image_url = COALESCE(?, image_url)
        WHERE id = ?""",
        (req.name, req.target_amount, req.deadline, req.image_url, goal_id)
    )

    # 3. 수정 후 최신 상태를 다시 읽어 응답에 담는다
    #    (API 관례: 수정 후엔 자원의 최신 상태를 돌려줌 → 프론트가 재호출 없이 화면 갱신)
    cursor.execute(
        """SELECT name, target_amount, current_amount, deadline, image_url
        FROM goals WHERE id = ?""",
        (goal_id,)
    )
    name, target_amount, current_amount, deadline, image_url = cursor.fetchone()

    conn.commit()
    conn.close()

    # 4. 파생 값은 저장하지 않고 매번 계산
    progress = round(current_amount / target_amount * 100, 1)
    d_day = (datetime.strptime(deadline, "%Y-%m-%d") - datetime.now()).days

    return {
        "id": goal_id,
        "name": name,
        "target_amount": target_amount,
        "current_amount": current_amount,
        "progress": progress,
        "d_day": d_day,
        "deadline": deadline,
        "image_url": image_url,
    }

@router.delete("/goals/current")
def delete_goal(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM goals WHERE user_id = ? AND is_completed = 0",
        (user_id,)
    )
    goal = cursor.fetchone()

    if goal is None:
        conn.close()
        raise HTTPException(status_code=404, detail="진행 중인 목표가 없습니다")
    goal_id = goal[0]

    cursor.execute("DELETE FROM savings WHERE goal_id = ?", (goal_id,))
    cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))

    conn.commit()
    conn.close()

    return {"message": "goal deleted"}

def days_before_deadline(deadline: str, completed_at: str) -> int:
    deadline_d = datetime.strptime(deadline, "%Y-%m-%d").date()
    completed_d = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S").date()
    return (deadline_d - completed_d).days

@router.get("/goals/history")
def get_goals_history(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    # 목록 조회는 조건으로 한 번에 (특정된 하나가 아니므로 2단계 불필요)
    cursor.execute(
        """SELECT id, name, target_amount, current_amount, deadline, image_url, completed_at
        FROM goals WHERE user_id = ? AND is_completed = 1
        ORDER BY completed_at DESC""",
        (user_id,)
    )
    goals_completed = cursor.fetchall()
    conn.close()

    # 빈 리스트 = "아직 달성한 목표 없음" — 에러 아닌 정상 응답
    return {"history": [
        {"id": g[0], "name": g[1], "target_amount": g[2], "current_amount": g[3],
         "progress": round(g[3] / g[2] * 100, 1),"deadline": g[4],
         "image_url": g[5], "completed_at": g[6],
         "days_early": days_before_deadline(g[4], g[6])}
        for g in goals_completed
    ]}

@router.get("/goals/{goal_id}/savings")
def get_goal_savings(goal_id: int, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM goals WHERE id = ? AND user_id = ?",
    (goal_id, user_id))
    if cursor.fetchone() is None :
        conn.close()
        raise HTTPException(status_code=404, detail= "목표를 찾을 수 없습니다")
    
    cursor.execute(
        """SELECT id, category, amount, memo, image_url, created_at
           FROM savings
           WHERE user_id = ? AND goal_id = ?
           ORDER BY created_at DESC""",
        (user_id, goal_id)
    )
    rows = cursor.fetchall()
    conn.close()

    return {"savings": [
        {"id": row[0], "category": row[1], "amount": row[2], "memo": row[3],
         "image_url": row[4], "created_at": row[5]}
        for row in rows
    ]}