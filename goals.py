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
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 미완료 목표가 있는지 검사 → 있으면 400 에러
    #    (힌트: conn.close() 잊지 말기)
    cursor.execute("SELECT id FROM goals WHERE user_id = ? AND is_completed = 0", (user_id,))
    if cursor.fetchone() is not None:
        conn.close()
        raise HTTPException(status_code= 400, detail= "이미 등록된 미완료 목표가 있습니다")

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
        """SELECT id, name, target_amount, current_amount, deadline, image_url, created_at
           FROM goals WHERE user_id = ? AND is_completed = 0""",
        (user_id,)
    )
    goal = cursor.fetchone()
    conn.close()

    if goal is None:
        raise HTTPException(status_code=404, detail="진행 중인 목표가 없습니다")

    goal_id, name, target_amount, current_amount, deadline, image_url, created_at = goal

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