import sys
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem, QMessageBox
)
from PySide6.QtCore import QTimer, QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPen, QTransform, QFont, QPainter


# CONFIGURATION

WINDOW_W, WINDOW_H = 1200, 700
RADAR_W, RADAR_H = 800, 700
SPAWN_INTERVAL_MS_START = 8000
UPDATE_INTERVAL_MS = 50
PLANE_SIZE = 12
SAFE_DISTANCE = 30
ALTITUDE_SAFE_DIFF = 300
LANDING_ZONE_RADIUS = 40
FUEL_CONSUMPTION_PER_TICK = 0.002
PIXEL_TO_KM = 0.03


# DATACLASS : Modèle avion

@dataclass
class PlaneModel:
    callsign: str
    x: float
    y: float
    heading: float
    speed_kmh: float
    altitude: int
    fuel: float
    landed: bool = False
    emergency: Optional[str] = None
    crashed: bool = False
    id: int = field(default_factory=lambda: random.randint(1000, 9999))

# ITEM GRAPHIQUE

class PlaneItem(QGraphicsEllipseItem):
    def __init__(self, model: PlaneModel):
        r = PLANE_SIZE
        super().__init__(-r/2, -r/2, r, r)
        self.model = model
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.update_visual()

    def update_visual(self):
        if self.model.landed:
            color = QColor(150, 150, 150)
        elif self.model.crashed:
            color = QColor(255, 100, 0)
        elif self.model.fuel < 10 or self.model.emergency:
            color = QColor(230, 40, 40)
        else:
            color = QColor(60, 180, 255)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.black, 1))
        transform = QTransform()
        transform.rotate(-self.model.heading)
        self.setTransform(transform)


# FENÊTRE PRINCIPALE