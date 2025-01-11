from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Order, Courier, Promocode, UserRole
from typing import List

admin_router = APIRouter(prefix="/admin", tags=["admin"])

def admin_required(user: User = Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return user

@admin_router.get("/statistics")
async def get_statistics(
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    total_orders = db.query(Order).count()
    active_couriers = db.query(Courier).filter(Courier.is_available == True).count()
    total_revenue = db.query(func.sum(Order.total_price))\
        .filter(Order.status == OrderStatus.DELIVERED).scalar() or 0
    
    return {
        "total_orders": total_orders,
        "active_couriers": active_couriers,
        "total_revenue": total_revenue
    }

@admin_router.post("/promocodes")
async def create_promocode(
    promocode: PromocodeCreate,
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    db_promocode = Promocode(**promocode.dict())
    db.add(db_promocode)
    db.commit()
    return db_promocode 