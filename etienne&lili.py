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

class TowerSim(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🛫 Simulateur Tour de Contrôle - IPSA")
        self.setGeometry(100, 100, WINDOW_W, WINDOW_H)

        # Radar
        self.scene = QGraphicsScene(0, 0, RADAR_W, RADAR_H)
        self.view = QGraphicsView(self.scene)
        self.view.setFixedSize(RADAR_W + 2, RADAR_H + 2)
        self.view.setRenderHints(self.view.renderHints() | QPainter.Antialiasing)
        self.scene.setBackgroundBrush(QColor(10, 15, 20))

        # Grille radar
        radar_pen = QPen(QColor(0, 255, 0, 40))
        for i in range(100, int(RADAR_W / 2), 100):
            self.scene.addEllipse(RADAR_W/2 - i, RADAR_H/2 - i, 2*i, 2*i, radar_pen)
        for i in range(0, RADAR_W, 100):
            self.scene.addLine(i, 0, i, RADAR_H, QPen(QColor(0, 255, 0, 25)))
        for j in range(0, RADAR_H, 100):
            self.scene.addLine(0, j, RADAR_W, j, QPen(QColor(0, 255, 0, 25)))

        # Zone d'atterrissage
        self.landing_center = QPointF(RADAR_W / 2, RADAR_H / 2)
        self.scene.addEllipse(
            self.landing_center.x() - LANDING_ZONE_RADIUS,
            self.landing_center.y() - LANDING_ZONE_RADIUS,
            LANDING_ZONE_RADIUS * 2,
            LANDING_ZONE_RADIUS * 2,
            pen=QPen(QColor(0, 255, 100)),
            brush=QBrush(QColor(0, 255, 0, 40))
        )

        # Données
        self.planes: List[PlaneModel] = []
        self.plane_items: dict[int, PlaneItem] = {}
        self.selected_plane_id: Optional[int] = None
        self.score = 0

        # Interface droite
        self.info_list = QListWidget()
        self.info_list.setFixedWidth(300)
        self.info_label = QLabel("Sélectionnez un avion")
        self.info_label.setStyleSheet("color: white; font-size: 12pt;")
        self.info_label.setWordWrap(True)

        title = QLabel("🛰️  Contrôle Radar")
        title.setStyleSheet("font-size: 14pt; color: #00FF80; font-weight: bold;")

        # Boutons
        self.btn_left = QPushButton("⟲ Virer Gauche")
        self.btn_right = QPushButton("Virer Droite ⟳")
        self.btn_climb = QPushButton("Monter ⬆")
        self.btn_descend = QPushButton("Descendre ⬇")
        self.btn_land = QPushButton("🛬 Atterrir")
        self.btn_end = QPushButton("⛔ Terminer Partie")

        buttons = [self.btn_left, self.btn_right, self.btn_climb, self.btn_descend, self.btn_land]
        for b in buttons:
            b.setEnabled(False)
            b.setStyleSheet("font-size: 10pt; padding:5px;")
        self.btn_end.setStyleSheet("background-color: #AA2222; color: white;")

        self.btn_left.clicked.connect(lambda: self.change_heading(-15))
        self.btn_right.clicked.connect(lambda: self.change_heading(15))
        self.btn_climb.clicked.connect(lambda: self.change_altitude(+500))
        self.btn_descend.clicked.connect(lambda: self.change_altitude(-500))
        self.btn_land.clicked.connect(self.try_land)
        self.btn_end.clicked.connect(self.end_game_forced)
        self.info_list.itemClicked.connect(self.list_item_clicked)

# Layout
        right_layout = QVBoxLayout()
        right_layout.addWidget(title)
        right_layout.addWidget(self.info_list)
        right_layout.addWidget(self.info_label)
        right_layout.addStretch()
        for b in buttons:
            right_layout.addWidget(b)
        right_layout.addWidget(self.btn_end)

        right_panel = QWidget()
        right_panel.setLayout(right_layout)
        right_panel.setStyleSheet("background-color: #111; color: white;")

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.view)
        main_layout.addWidget(right_panel)
        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # Timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_simulation)
        self.update_timer.start(UPDATE_INTERVAL_MS)

        self.spawn_timer = QTimer()
        self.spawn_timer.timeout.connect(self.spawn_plane)
        self.spawn_timer.start(SPAWN_INTERVAL_MS_START)

        self.scene.selectionChanged.connect(self.scene_selection_changed)
        for _ in range(2):
            self.spawn_plane()

        self.status = self.statusBar()
        self.status.setStyleSheet("color: white; background-color: #222;")
        self.update_status()


    def update_status(self):
        self.status.showMessage(f"Score: {self.score} | Avions actifs: {len(self.planes)}")

    def _generate_callsign(self):
        prefixes = ["AF", "BA", "LH", "EN", "FR", "IP", "QA"]
        return random.choice(prefixes) + str(random.randint(100, 999))


    def spawn_plane(self):
        """Spawn d'un avion avec vérification de distance minimale"""
        edge = random.choice(['top', 'bottom', 'left', 'right'])
        margin = 10
        attempt = 0
        while True:
            attempt += 1
            if edge == 'top':
                x, y, heading = random.uniform(0, RADAR_W), -margin, random.uniform(120, 240)
            elif edge == 'bottom':
                x, y, heading = random.uniform(0, RADAR_W), RADAR_H + margin, random.uniform(-60, 60)
            elif edge == 'left':
                x, y, heading = -margin, random.uniform(0, RADAR_H), random.uniform(-30, 30)
            else:
                x, y, heading = RADAR_W + margin, random.uniform(0, RADAR_H), random.uniform(150, 210)
            if all(math.hypot(p.x - x, p.y - y) > 80 for p in self.planes) or attempt > 10:
                break

        callsign = self._generate_callsign()
        speed_kmh = random.uniform(200, 600)
        altitude = random.choice([2000, 3000, 4000, 5000])
        fuel = random.uniform(40, 100)
        model = PlaneModel(callsign, x, y, heading % 360, speed_kmh, altitude, fuel)
        self.planes.append(model)

        item = PlaneItem(model)
        item.setPos(model.x, model.y)
        self.scene.addItem(item)
        self.plane_items[model.id] = item

        lw_item = QListWidgetItem(f"{model.callsign} | Alt {model.altitude}m | {int(model.speed_kmh)} km/h | Fuel {int(model.fuel)}%")
        lw_item.setData(Qt.UserRole, model.id)
        self.info_list.addItem(lw_item)


    def update_simulation(self):
        dt = UPDATE_INTERVAL_MS / 1000.0
        to_remove = []

        for model in list(self.planes):
            if model.landed or model.crashed:
                continue
                # consommation carburant ajustée selon la vitesse
                model.fuel -= FUEL_CONSUMPTION_PER_TICK * (model.speed_kmh / 400)
                if model.fuel <= 0:
                    model.fuel = 0
                    model.emergency = "Panne carburant"
                    model.crashed = True
                    self.schedule_removal(model)
                    continue

                if model.altitude < 100:
                    model.crashed = True
                    model.emergency = "Crash au sol"
                    self.schedule_removal(model)
                    continue

                # déplacement km/h -> px/s
                speed_px_s = (model.speed_kmh / 3.6) / (PIXEL_TO_KM * 1000)
                rad = math.radians(model.heading)
                model.x += math.cos(rad) * speed_px_s * dt
                model.y += math.sin(rad) * speed_px_s * dt

                item = self.plane_items.get(model.id)
                if item:
                    item.setPos(model.x, model.y)
                    item.update_visual()

                margin = 100
                if model.x < -margin or model.x > RADAR_W + margin or model.y < -margin or model.y > RADAR_H + margin:
                    to_remove.append(model)

                # Collisions
            for i in range(len(self.planes)):
                for j in range(i + 1, len(self.planes)):
                    a, b = self.planes[i], self.planes[j]
                    if a.landed or b.landed or a.crashed or b.crashed:
                        continue
                    if math.hypot(a.x - b.x, a.y - b.y) < SAFE_DISTANCE and abs(
                            a.altitude - b.altitude) < ALTITUDE_SAFE_DIFF:
                        self.handle_collision(a, b)
                        return

            for m in to_remove:
                self.remove_plane(m, penalize=False)