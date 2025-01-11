from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket
from sqlalchemy.orm import Session
from typing import List
from database import get_db, init_db
from models import Customer, Order, OrderItem, User, Courier, OrderStatus, Order, TrackingUpdate, Notification, UserRole, Review
from pydantic import BaseModel, EmailStr
from fastapi.security import OAuth2PasswordRequestForm
from auth import create_access_token, get_current_user
from datetime import timedelta, datetime
from pydantic import validator
from fastapi.middleware.cors import CORSMiddleware
from rate_limiter import rate_limit
from cache import get_cached_data, set_cached_data
from payment_service import PaymentService, PaymentError
from logger import logger
from fastapi import WebSocketDisconnect
from tracking.gps_tracker import gps_tracker

app = FastAPI(
    title="Delivery Service API",
    description="API для сервиса доставки",
    version="1.0.0"
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    await rate_limit(request)
    response = await call_next(request)
    return response

class CustomerCreate(BaseModel):
    name: str
    address: str
    phone: str
    email: EmailStr
    
    class Config:
        min_length_name = 2
        max_length_name = 100

class OrderCreate(BaseModel):
    customer_id: int
    delivery_address: str
    items: List[dict]
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Заказ должен содержать хотя бы один товар')
        for item in v:
            if not all(k in item for k in ('product_name', 'quantity', 'price')):
                raise ValueError('Каждый товар должен иметь name, quantity и price')
            if item['quantity'] <= 0:
                raise ValueError('Количество товара должно быть больше 0')
            if item['price'] <= 0:
                raise ValueError('Цена товара должна быть больше 0')
        return v

class PaymentCreate(BaseModel):
    order_id: int
    payment_method: str
    amount: float

class ReviewCreate(BaseModel):
    rating: int
    comment: str

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
async def create_order(order: OrderCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Проверяем существование клиента
    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
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
async def get_order(order_id: int, db: Session = Depends(get_db)):
    cache_key = f"order:{order_id}"
    cached_order = get_cached_data(cache_key)
    
    if cached_order:
        return cached_order
        
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    order_data = jsonable_encoder(order)
    set_cached_data(cache_key, order_data)
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
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        status, payment_id = await PaymentService.process_payment(
            amount=payment.amount,
            currency="RUB",
            payment_method=payment.payment_method,
            order_id=str(order_id)
        )
        
        order.payment_status = status
        order.payment_id = payment_id
        db.commit()
        
        return {"status": status, "payment_id": payment_id}
        
    except PaymentError as e:
        logger.error(f"Payment failed for order {order_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

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

@app.post("/orders/{order_id}/review")
async def create_review(
    order_id: int,
    review: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
        
    if order.status != OrderStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Можно оставить отзыв только о доставленном заказе")
    
    db_review = Review(
        order_id=order_id,
        customer_id=current_user.id,
        courier_id=order.courier_id,
        rating=review.rating,
        comment=review.comment
    )
    db.add(db_review)
    db.commit()
    
    return db_review

@app.websocket("/ws/courier/{courier_id}/location")
async def websocket_courier_location(
    websocket: WebSocket,
    courier_id: int,
    db: Session = Depends(get_db)
):
    await gps_tracker.connect(courier_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await gps_tracker.update_location(
                courier_id=courier_id,
                latitude=data["latitude"],
                longitude=data["longitude"],
                db=db
            )
    except WebSocketDisconnect:
        gps_tracker.disconnect(courier_id) 