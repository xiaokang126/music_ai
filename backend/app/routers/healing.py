from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..middleware.auth import get_current_user
from ..services.healing_service import get_all_plans, start_plan, get_my_plan, complete_task

router = APIRouter(prefix="/api/healing", tags=["healing"])


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = get_all_plans(db)
    return [{"id": p.id, "name": p.name, "description": p.description,
             "duration_days": p.duration_days, "cover_icon": p.cover_icon,
             "tasks_json": p.tasks_json} for p in plans]


@router.post("/start")
def start_healing_plan(plan_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    result, error = start_plan(db, user.id, plan_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {
        "id": result.id, "user_id": result.user_id, "plan_id": result.plan_id,
        "current_day": result.current_day, "start_date": result.start_date.isoformat(),
        "completed_tasks_json": result.completed_tasks_json, "is_completed": result.is_completed
    }


@router.get("/my")
def my_plan(db: Session = Depends(get_db), user=Depends(get_current_user)):
    plan = get_my_plan(db, user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan")
    return plan


@router.post("/tasks/{uph_id}/complete")
def complete_healing_task(uph_id: int, day: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ok = complete_task(db, uph_id, day)
    if not ok:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "completed"}
