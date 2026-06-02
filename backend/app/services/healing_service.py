import json
from sqlalchemy.orm import Session
from ..models.healing_plan import HealingPlan, UserHealingPlan


def get_all_plans(db: Session):
    return db.query(HealingPlan).all()


def start_plan(db: Session, user_id: int, plan_id: int):
    existing = db.query(UserHealingPlan).filter(
        UserHealingPlan.user_id == user_id,
        UserHealingPlan.is_completed == 0
    ).first()
    if existing:
        return None, "You already have an active plan"

    uph = UserHealingPlan(user_id=user_id, plan_id=plan_id, current_day=1)
    db.add(uph)
    db.commit()
    db.refresh(uph)
    return uph, None


def get_my_plan(db: Session, user_id: int):
    uph = db.query(UserHealingPlan).filter(
        UserHealingPlan.user_id == user_id,
        UserHealingPlan.is_completed == 0
    ).first()
    if not uph:
        return None
    plan = db.query(HealingPlan).filter(HealingPlan.id == uph.plan_id).first()
    result = {
        "id": uph.id, "user_id": uph.user_id, "plan_id": uph.plan_id,
        "current_day": uph.current_day, "start_date": uph.start_date,
        "completed_tasks_json": uph.completed_tasks_json,
        "is_completed": uph.is_completed,
        "plan_name": plan.name if plan else "",
        "duration_days": plan.duration_days if plan else 0,
        "tasks_json": plan.tasks_json if plan else "[]"
    }
    return result


def complete_task(db: Session, uph_id: int, day: int):
    uph = db.query(UserHealingPlan).filter(UserHealingPlan.id == uph_id).first()
    if not uph:
        return False

    completed = json.loads(uph.completed_tasks_json) if uph.completed_tasks_json else []
    if day not in completed:
        completed.append(day)
    uph.completed_tasks_json = json.dumps(completed)

    plan = db.query(HealingPlan).filter(HealingPlan.id == uph.plan_id).first()
    if plan and len(completed) >= plan.duration_days:
        uph.is_completed = 1
    else:
        uph.current_day = day + 1

    db.commit()
    return True
