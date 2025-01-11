from fastapi import WebSocket
from models import CourierLocation
from sqlalchemy.orm import Session
import json

class GPSTracker:
    def __init__(self):
        self.active_connections: dict = {}  # courier_id: WebSocket

    async def connect(self, courier_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[courier_id] = websocket

    def disconnect(self, courier_id: int):
        self.active_connections.pop(courier_id, None)

    async def update_location(self, courier_id: int, latitude: float, longitude: float, db: Session):
        location = CourierLocation(
            courier_id=courier_id,
            latitude=latitude,
            longitude=longitude
        )
        db.add(location)
        db.commit()

        # Отправляем обновление всем подписчикам
        if courier_id in self.active_connections:
            await self.active_connections[courier_id].send_json({
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": location.timestamp.isoformat()
            })

gps_tracker = GPSTracker() 