import math
import sys
import threading

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsRectItem,
    QGraphicsLineItem
)
from PyQt5.QtGui import QBrush, QColor, QPolygonF, QPen
from PyQt5.QtCore import QTimer, QPointF, Qt
import pyqtgraph as pg
from SerParse import *
from SerialWorker import *

class ValveSymbol(QGraphicsPolygonItem):
    def __init__(self, center_x, center_y, orientation='horizontal'):
        super().__init__()

        size = 30
        if orientation == 'horizontal':
            triangle1 = QPolygonF([
                QPointF(center_x, center_y),
                QPointF(center_x - size, center_y - size),
                QPointF(center_x - size, center_y + size)
            ])
            triangle2 = QPolygonF([
                QPointF(center_x, center_y),
                QPointF(center_x + size, center_y - size),
                QPointF(center_x + size, center_y + size)
            ])
        else:
            triangle1 = QPolygonF([
                QPointF(center_x, center_y),
                QPointF(center_x - size, center_y - size),
                QPointF(center_x + size, center_y - size)
            ])
            triangle2 = QPolygonF([
                QPointF(center_x, center_y),
                QPointF(center_x - size, center_y + size),
                QPointF(center_x + size, center_y + size)
            ])

        self.triangle1_item = QGraphicsPolygonItem(triangle1)
        self.triangle2_item = QGraphicsPolygonItem(triangle2)
        self.triangle1_item.setBrush(QBrush(QColor("gray")))
        self.triangle2_item.setBrush(QBrush(QColor("gray")))

    def add_to_scene(self, scene):
        scene.addItem(self.triangle1_item)
        scene.addItem(self.triangle2_item)

    def toggle_color(self):
        current_color = self.triangle1_item.brush().color().name()
        new_color = "green" if current_color == "#808080" else "gray"
        self.triangle1_item.setBrush(QBrush(QColor(new_color)))
        self.triangle2_item.setBrush(QBrush(QColor(new_color)))


class PumpSymbol(QGraphicsRectItem):
    def __init__(self, center_x, center_y):
        size = 40
        super().__init__(center_x - size / 2, center_y - size / 2, size, size)
        self.setBrush(QBrush(QColor("lightblue")))

        circle = QGraphicsEllipseItem(center_x - size / 4, center_y - size / 4, size / 2, size / 2)
        circle.setBrush(QBrush(QColor("blue")))
        self.circle = circle

    def add_to_scene(self, scene):
        scene.addItem(self)
        scene.addItem(self.circle)


class VacuumGauge:
    def __init__(self, center_x, center_y, radius=30):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius

        # Круг вакууметра
        self.circle = QGraphicsEllipseItem(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        self.circle.setPen(QPen(Qt.black, 2))

        # Стрелка
        self.arrow = QGraphicsLineItem()
        self.arrow.setPen(QPen(Qt.red, 2))
        self.set_angle(0)  # начальный угол

    def set_angle(self, angle_deg):
        # Угол в градусах, 0 = вправо, 90 = вверх
        angle_rad = math.radians(angle_deg)
        end_x = self.center_x + self.radius * math.cos(angle_rad)
        end_y = self.center_y - self.radius * math.sin(angle_rad)
        self.arrow.setLine(self.center_x, self.center_y, end_x, end_y)

    def add_to_scene(self, scene):
        scene.addItem(self.circle)
        scene.addItem(self.arrow)


class SchematicWidget(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 400, 400)

        # Используем символ клапана
        self.valve_item = ValveSymbol(200, 200, orientation='horizontal')
        self.valve_item.add_to_scene(self.scene)

        # Добавим насос
        self.pump_item = PumpSymbol(100, 100)
        self.pump_item.add_to_scene(self.scene)

        self.vacuum_gauge = VacuumGauge(300, 100)
        self.vacuum_gauge.add_to_scene(self.scene)

    def toggle_valve(self):
        self.valve_item.toggle_color()


class GraphPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.plots = []
        self.curves = []
        self.vlines = []
        self.data = []

        for i in range(3):
            plot = pg.PlotWidget()
            curve = plot.plot(np.zeros(100), pen='g')
            vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('r', width=1.5))
            plot.addItem(vline)

            self.plots.append(plot)
            self.curves.append(curve)
            self.vlines.append(vline)
            self.data.append(np.zeros(100))
            layout.addWidget(plot)

        self.current_index = 0
        self.mark_requested = False

    def update_plots(self, actual_data):
        if self.current_index > 0:
            self.current_index -= 1
        for i in range(3):
            self.data[i] = np.roll(self.data[i], -1)
            self.data[i][-1] = actual_data[i]
            self.curves[i].setData(self.data[i])
            if self.current_index:
                self.vlines[i].setValue(self.current_index)

    def mark_event(self):
        self.mark_requested = True
        self.current_index = 100  # Сброс позиции метки, чтобы она шла с начала данных


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCADA NIIM")
        self.setGeometry(100, 100, 1280, 1024)
        self.setup_ui()

        # Переменные для работы с последовательным портом
        self.serial_thread = None
        self.serial_worker = None

        self.start_serial_thread()

    def setup_ui(self):
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # === Block 1: Control Panel with Scroll ===
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidget(control_panel)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(200)

        self.valve_button = QPushButton("Открыть клапан")
        self.valve_button.clicked.connect(self.toggle_valve)
        control_layout.addWidget(self.valve_button)

        # === Block 2: Schematic Widget ===
        self.schematic = SchematicWidget()

        # === Block 3: Graph Panel with 4 Graphs ===
        self.graph_panel = GraphPanel()

        # Add blocks to main layout
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.schematic, stretch=2)
        main_layout.addWidget(self.graph_panel, stretch=1)

    def display_data(self, data):
        self.graph_panel.update_plots([data["MIDA"], data["Magdischarge"], data["ThermalIndicator"]])

    def display_error(self, error_msg):
        print(error_msg)

    def update_connection_status(self, connected):
        print(connected)

    def start_serial_thread(self):
        # Создаем рабочий объект и поток
        self.serial_worker = SerialWorker()
        self.serial_thread = QThread()

        # Перемещаем worker в поток
        self.serial_worker.moveToThread(self.serial_thread)

        # Подключаем сигналы
        self.serial_worker.data_received.connect(self.display_data)
        self.serial_worker.error_occurred.connect(self.display_error)
        self.serial_worker.connection_status.connect(self.update_connection_status)

        # Подключаем методы потока
        self.serial_thread.started.connect(self.serial_worker.connect_serial)
        self.serial_thread.started.connect(self.serial_worker.read_serial_data)

        # Запускаем поток
        self.serial_thread.start()

    def stop_serial_thread(self):
        if self.serial_worker:
            self.serial_worker.stop()
        if self.serial_thread:
            self.serial_thread.quit()
            self.serial_thread.wait()

        self.serial_worker = None
        self.serial_thread = None
        self.connect_btn.setText("Connect")


    def toggle_valve(self):
        self.schematic.toggle_valve()
        self.graph_panel.mark_event()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
