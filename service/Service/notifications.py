from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db, init_db
from models import Customer, Order, OrderItem, User, Courier, OrderStatus, Order, TrackingUpdate, Notification
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from auth import create_access_token, get_current_user
from datetime import timedelta

app = FastAPI()

class CustomerCreate(BaseModel):
    name: str
    address: str
    phone: str
    email: str

class OrderCreate(BaseModel):
    customer_id: int
    delivery_address: str
    items: List[dict]

class PaymentCreate(BaseModel):
    order_id: int
    payment_method: str
    amount: float

@app.on_event("startup")
async def startup():
    init_db()

@app.post("/customers/")
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    db_customer = Customer(**customer.dict())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

@app.post("/orders/")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # Вычисление общей стоимости
    total_price = sum(item["price"] * item["quantity"] for item in order.items)
    
    # Создание заказа
    db_order = Order(
        customer_id=order.customer_id,
        delivery_address=order.delivery_address,
        total_price=total_price
    )
    db.add(db_order)
    db.commit()
    
    # Добавление позиций заказа
    for item in order.items:
        order_item = OrderItem(
            order_id=db_order.id,
            product_name=item["product_name"],
            quantity=item["quantity"],
            price=item["price"]
        )
        db.add(order_item)
    
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order 

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.check_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/orders/{order_id}/pay")
async def process_payment(
    order_id: int,
    payment: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    # Здесь должна быть интеграция с платежной системой
    # Пример:
    payment_id = f"PAY-{order_id}-{datetime.utcnow().timestamp()}"
    
    order.payment_status = "paid"
    order.payment_id = payment_id
    order.status = OrderStatus.PAID
    db.commit()
    
    return {"status": "success", "payment_id": payment_id}

@app.post("/orders/{order_id}/assign-courier")
async def assign_courier(
    order_id: int,
    courier_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    order = db.query(Order).filter(Order.id == order_id).first()
    courier = db.query(Courier).filter(Courier.id == courier_id).first()
    
    if not order or not courier:
        raise HTTPException(status_code=404, detail="Заказ или курьер не найден")
    
    order.courier_id = courier_id
    order.status = OrderStatus.ASSIGNED_TO_COURIER
    db.commit()
    
    # Создаем уведомление для курьера
    notification = Notification(
        user_id=courier.user_id,
        order_id=order_id,
        type="new_assignment",
        message=f"Вам назначен новый заказ #{order_id}"
    )
    db.add(notification)
    db.commit()
    
    return {"status": "success"}

@app.post("/orders/{order_id}/tracking")
async def add_tracking_update(
    order_id: int,
    location: str,
    status: OrderStatus,
    comment: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.COURIER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    tracking_update = TrackingUpdate(
        order_id=order_id,
        status=status,
        location=location,
        comment=comment
    )
    db.add(tracking_update)
    
    order = db.query(Order).filter(Order.id == order_id).first()
    order.status = status
    if status == OrderStatus.DELIVERED:
        order.actual_delivery_time = datetime.utcnow()
    
    db.commit()
    
    return {"status": "success"}

@app.get("/notifications/")
async def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifications = db.query(Notification)\
        .filter(Notification.user_id == current_user.id)\
        .order_by(Notification.created_at.desc())\
        .all()
    return notifications 