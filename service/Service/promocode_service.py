from datetime import datetime
from sqlalchemy.orm import Session
from models import Promocode, PromoCodeUse
from fastapi import HTTPException

class PromocodeService:
    @staticmethod
    async def apply_promocode(code: str, order_total: float, db: Session) -> float:
        promocode = db.query(Promocode).filter(
            Promocode.code == code,
            Promocode.is_active == True,
            Promocode.valid_from <= datetime.utcnow(),
            Promocode.valid_to >= datetime.utcnow()
        ).first()
        
        if not promocode:
            raise HTTPException(status_code=404, detail="Промокод не найден или истек")
            
        if promocode.max_uses and promocode.current_uses >= promocode.max_uses:
            raise HTTPException(status_code=400, detail="Промокод больше не действителен")
        
        # Рассчитываем скидку
        if promocode.discount_percent:
            discount = order_total * (promocode.discount_percent / 100)
        else:
            discount = promocode.discount_amount
            
        return max(0, order_total - discount) 