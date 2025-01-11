from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), unique=True)
    orders = relationship("Order", back_populates="customer")

class UserRole(str, Enum):
    CUSTOMER = "customer"
    COURIER = "courier"
    ADMIN = "admin"

class OrderStatus(str, Enum):
    NEW = "new"
    PAID = "paid"
    PREPARING = "preparing"
    ASSIGNED_TO_COURIER = "assigned_to_courier"
    IN_DELIVERY = "in_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.CUSTOMER)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Courier(Base):
    __tablename__ = 'couriers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    is_available = Column(Boolean, default=True)
    current_location = Column(String(200))
    
    user = relationship("User")
    deliveries = relationship("Order", back_populates="courier")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('customers.id'))
    courier_id = Column(Integer, ForeignKey('couriers.id'), nullable=True)
    status = Column(String(50), default=OrderStatus.NEW)
    created_at = Column(DateTime, default=datetime.utcnow)
    delivery_address = Column(String(200), nullable=False)
    total_price = Column(Float, nullable=False)
    payment_status = Column(String(50), default='pending')
    payment_id = Column(String(100), nullable=True)
    estimated_delivery_time = Column(DateTime, nullable=True)
    actual_delivery_time = Column(DateTime, nullable=True)
    
    customer = relationship("Customer", back_populates="orders")
    courier = relationship("Courier", back_populates="deliveries")
    items = relationship("OrderItem", back_populates="order")
    tracking_updates = relationship("TrackingUpdate", back_populates="order")
    
    __table_args__ = (
        Index('idx_customer_id', 'customer_id'),
        Index('idx_courier_id', 'courier_id'),
        Index('idx_status', 'status'),
    )

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="items") 

class TrackingUpdate(Base):
    __tablename__ = 'tracking_updates'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    status = Column(String(50), nullable=False)
    location = Column(String(200))
    timestamp = Column(DateTime, default=datetime.utcnow)
    comment = Column(String(500))
    
    order = relationship("Order", back_populates="tracking_updates")

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    type = Column(String(50), nullable=False)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False) 
    
    __table_args__ = (
        Index('idx_user_notifications', 'user_id', 'created_at'),
    ) 

class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'))
    courier_id = Column(Integer, ForeignKey('couriers.id'))
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("Order", back_populates="reviews")
    customer = relationship("Customer", back_populates="reviews")
    courier = relationship("Courier", back_populates="reviews")

class CourierLocation(Base):
    __tablename__ = 'courier_locations'
    
    id = Column(Integer, primary_key=True)
    courier_id = Column(Integer, ForeignKey('couriers.id'))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    courier = relationship("Courier", back_populates="locations")

class Promocode(Base):
    __tablename__ = 'promocodes'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    discount_percent = Column(Float)
    discount_amount = Column(Float)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=False)
    max_uses = Column(Integer)
    current_uses = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

class PromoCodeUse(Base):
    __tablename__ = 'promocode_uses'
    
    id = Column(Integer, primary_key=True)
    promocode_id = Column(Integer, ForeignKey('promocodes.id'))
    order_id = Column(Integer, ForeignKey('orders.id'))
    used_at = Column(DateTime, default=datetime.utcnow) 