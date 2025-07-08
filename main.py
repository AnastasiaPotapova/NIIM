import math
import sys
import threading
import random

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsRectItem,
    QGraphicsLineItem, QGraphicsTextItem, QMenuBar, QAction, qApp, QGridLayout, QStackedWidget, QTableWidgetItem,
    QTableWidget, QLineEdit, QLabel
)
from PyQt5.QtGui import QBrush, QColor, QPolygonF, QPen, QFont, QPainter
from PyQt5.QtCore import QTimer, QPointF, Qt
import pyqtgraph as pg
from SerialWorker import *

class ValveSymbol(QGraphicsPolygonItem):
    def __init__(self, label, set, center_x, center_y, orientation='h'):
        super().__init__()

        size = 20
        self.center_x = center_x
        self.center_y = center_y
        self.orientation = orientation

        if orientation == 'h':
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

        # Добавляем подпись слева от клапана
        self.label_item = QGraphicsTextItem(label)
        font = QFont()
        font.setBold(True)
        self.label_item.setFont(font)
        if set == "l":
            label_x = center_x - size - 30
            label_y = center_y - 10
        elif set == "r":
            label_x = center_x + size
            label_y = center_y - 10
        elif set == "t":
            label_x = center_x - 10
            label_y = center_y - size - 30
        else:
            label_x = center_x - 10
            label_y = center_y + size + 30
        self.label_item.setPos(label_x, label_y)

    def add_to_scene(self, scene):
        scene.addItem(self.triangle1_item)
        scene.addItem(self.triangle2_item)
        scene.addItem(self.label_item)

    def toggle_color(self):
        current_color = self.triangle1_item.brush().color().name()
        new_color = "green" if current_color == "#808080" else "gray"
        self.triangle1_item.setBrush(QBrush(QColor(new_color)))
        self.triangle2_item.setBrush(QBrush(QColor(new_color)))

class PumpSymbol(QGraphicsRectItem):
    def __init__(self, name, center_x, center_y):
        size = 40
        super().__init__(center_x - size / 2, center_y - size / 2, size, size)
        self.setBrush(QBrush(QColor("lightblue")))

        circle = QGraphicsEllipseItem(center_x - size / 4, center_y - size / 4, size / 2, size / 2)
        circle.setBrush(QBrush(QColor("blue")))
        self.circle = circle

        self.label_item = QGraphicsTextItem(name)
        font = QFont()
        font.setBold(True)
        self.label_item.setFont(font)
        self.label_item.setPos(center_x - size - 5, center_y - 10)

    def add_to_scene(self, scene):
        scene.addItem(self)
        scene.addItem(self.circle)
        scene.addItem(self.label_item)

class VacuumGauge:
    def __init__(self, name, set, center_x, center_y, radius=15):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius

        # Заполненный белый круг
        self.circle = QGraphicsEllipseItem(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        self.circle.setPen(QPen(Qt.black, 2))
        self.circle.setBrush(QBrush(QColor("white")))

        # Красная стрелка
        self.arrow = QGraphicsLineItem()
        self.arrow.setPen(QPen(Qt.red, 2))
        self.set_angle(0)

        self.label = QGraphicsTextItem(name)
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)
        if set == "l":
            label_x = center_x - radius - 30
            label_y = center_y - 10
        elif set == "r":
            label_x = center_x + radius + 30
            label_y = center_y - 10
        elif set == "t":
            label_x = center_x - 10
            label_y = center_y - radius - 30
        else:
            label_x = center_x - 10
            label_y = center_y + radius + 30
        self.label.setPos(label_x, label_y)

    def set_angle(self, angle_deg):
        angle_rad = math.radians(angle_deg)
        end_x = self.center_x + self.radius * math.cos(angle_rad)
        end_y = self.center_y - self.radius * math.sin(angle_rad)
        self.arrow.setLine(self.center_x, self.center_y, end_x, end_y)

    def add_to_scene(self, scene):
        scene.addItem(self.circle)
        scene.addItem(self.arrow)
        scene.addItem(self.label)

class SchematicWidget(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 400, 400)
        self.items = {}

        # Добавим насос
        self.items["NR"] = PumpSymbol("NR", 60, 220)
        self.items["NR"].add_to_scene(self.scene)

        self.items["NI"] = PumpSymbol("NI", 140, 380)
        self.items["NI"].add_to_scene(self.scene)

        # Используем символ клапана
        self.items["V1"] = ValveSymbol("V1", "l", 140, 340, orientation='v')
        self.items["V1"].add_to_scene(self.scene)

        self.items["V2"] = ValveSymbol("V2", "l",60, 180, orientation='v')
        self.items["V2"].add_to_scene(self.scene)

        self.items["V3"] = ValveSymbol("V3", "l", 60, 260, orientation='v')
        self.items["V3"].add_to_scene(self.scene)

        self.items["V4"] = ValveSymbol("V4", "t",180, 100, orientation='h')
        self.items["V4"].add_to_scene(self.scene)

        self.items["V5"] = ValveSymbol("V5", "r", 140, 140, orientation='v')
        self.items["V5"].add_to_scene(self.scene)

        self.items["V6"] = ValveSymbol("V6", "t",20, 20, orientation='v')
        self.items["V6"].add_to_scene(self.scene)

        self.items["V7"] = ValveSymbol("V7", "t", 100, 20, orientation='v')
        self.items["V7"].add_to_scene(self.scene)

        self.items["V8"] = ValveSymbol("V8", "t", 260, 100, orientation='h')
        self.items["V8"].add_to_scene(self.scene)

        self.items["VF"] = ValveSymbol("VF", "t", 300, 100, orientation='h')
        self.items["VF"].add_to_scene(self.scene)

        self.items["CV1"] = QGraphicsRectItem(0, 40, 120, 120)
        self.items["CV1"].setBrush(QBrush(QColor("lightblue")))
        self.scene.addItem(self.items["CV1"])

        self.items["P1"] = VacuumGauge("P1", "t",180, 300)
        self.items["P1"].add_to_scene(self.scene)

        self.items["P2"] = VacuumGauge("P2", "t",220, 100)
        self.items["P2"].add_to_scene(self.scene)

        self.items["P3"] = VacuumGauge("P3", "t", 140, 60)
        self.items["P3"].add_to_scene(self.scene)

        self.draw_line(60, 280, 60, 300)
        self.draw_line(160, 300, 60, 300)
        self.draw_line(140, 320, 140, 160)
        self.draw_line(140, 80, 140, 120)
        self.draw_line(120, 100, 160, 100)

    def draw_line(self, x1, y1, x2, y2):
        line = self.scene.addLine(x1, y1, x2, y2)

        # Настраиваем внешний вид линии
        pen = QPen(Qt.red)  # Красный цвет
        pen.setWidth(1)  # Толщина 3 пикселя
        line.setPen(pen)

    def toggle_valve(self, name):
        self.items[name].toggle_color()

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

class EepromWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Данные EEPROM")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Поля ввода начала и конца
        input_layout = QHBoxLayout()
        self.start_input = QLineEdit()
        self.end_input = QLineEdit()
        self.start_input.setPlaceholderText("Начальный индекс")
        self.end_input.setPlaceholderText("Конечный индекс")
        input_layout.addWidget(QLabel("От:"))
        input_layout.addWidget(self.start_input)
        input_layout.addWidget(QLabel("До:"))
        input_layout.addWidget(self.end_input)

        self.layout.addLayout(input_layout)

        buttons_layout = QHBoxLayout()
        self.generate_button = QPushButton("Прочитать")
        self.generate_button.clicked.connect(self.generate_table)
        buttons_layout.addWidget(self.generate_button)

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.save_table)
        buttons_layout.addWidget(self.save_button)

        self.layout.addLayout(buttons_layout)

        self.table = QTableWidget()
        self.layout.addWidget(self.table)

    def generate_table(self):
        try:
            start = int(self.start_input.text())
            end = int(self.end_input.text())
            if start > end:
                raise ValueError("Начальный индекс должен быть меньше или равен конечному.")
        except ValueError:
            self.start_input.setText("")
            self.end_input.setText("")
            self.start_input.setPlaceholderText("Ошибка: введите числа")
            self.end_input.setPlaceholderText("Ошибка: введите числа")
            return

        count = end - start + 1
        self.table.setRowCount(count)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Индекс", "Ox", "Od"])

        for i, index in enumerate(range(start, end + 1)):
            # Ячейки редактируемые по умолчанию
            self.table.setItem(i, 0, QTableWidgetItem(str(index)))
            self.table.setItem(i, 1, QTableWidgetItem(str(random.randint(0, 100))))
            self.table.setItem(i, 2, QTableWidgetItem(str(random.randint(0, 100))))

    def save_table(self):
        rows = self.table.rowCount()
        cols = self.table.columnCount()

        result = []
        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table.item(row, col)
                text = item.text() if item else ""
                row_data.append(text)
            result.append(row_data)

        # Пример: выводим результат в консоль
        print("Сохранённые данные:")
        for r in result:
            print(r)


class ConfigWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Конфигурация")
        self.setFixedSize(400, 300)
        self.layout = QVBoxLayout(self)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # 2 столбца данных + 1 столбец для кнопки
        self.table.setHorizontalHeaderLabels(["Параметр", "Значение", ""])  # третий без названия
        self.layout.addWidget(self.table)

        # Начальные 3 строки
        for _ in range(3):
            self.add_row()

        # Кнопка добавления
        self.add_button = QPushButton("Добавить строку")
        self.add_button.clicked.connect(self.add_row)
        self.layout.addWidget(self.add_button)
        self.save_button = QPushButton("Сохранить")
        self.layout.addWidget(self.save_button)

    def add_row(self):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        # Редактируемые ячейки
        self.table.setItem(row_position, 0, QTableWidgetItem(""))
        self.table.setItem(row_position, 1, QTableWidgetItem(""))

        # Кнопка удаления
        delete_button = QPushButton("🗙")
        delete_button.setStyleSheet("color: red; font-weight: bold;")
        delete_button.clicked.connect(lambda _, r=row_position: self.delete_row(r))
        self.table.setCellWidget(row_position, 2, delete_button)

    def delete_row(self, row):
        self.table.removeRow(row)

        # После удаления пересоздаем кнопки, чтобы lambda не хранил старые индексы
        for r in range(self.table.rowCount()):
            button = QPushButton("🗙")
            button.setStyleSheet("color: red; font-weight: bold;")
            button.clicked.connect(lambda _, row=r: self.delete_row(row))
            self.table.setCellWidget(r, 2, button)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCADA NIIM")
        self.setGeometry(100, 100, 1280, 1024)
        self.setup_ui()
        self.mode = 0
        # Переменные для работы с последовательным портом
        self.serial_thread = None
        self.serial_worker = None

        self.start_serial_thread()

    def setup_ui(self):
        main_layout = QGridLayout()
        work_panel = QWidget()
        work_layout = QHBoxLayout()
        work_panel.setLayout(work_layout)
        self.setLayout(main_layout)

        menubar = QMenuBar()
        actionFile = menubar.addMenu("Режим работы")
        avto = actionFile.addAction("Автоматический")
        avto.triggered.connect(self.setAvto)
        pro = actionFile.addAction("Продвинутый")
        pro.triggered.connect(self.setPro)
        EepromBar = menubar.addMenu("ЭСППЗУ")
        EepromWrite = EepromBar.addAction("Записать")

        EepromRead = EepromBar.addAction("Прочитать")
        EepromRead.triggered.connect(self.ReadEeprom)

        Config = menubar.addAction("Редактировать конфигурацию")
        Config.triggered.connect(self.ReadConfig)

        menubar.addMenu("Логи")

        # === Block 1: Control Panel with Scroll ===
        self.work_control = QStackedWidget()


        control_panel = QWidget()
        self.work_control.addWidget(control_panel)
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.work_control)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(200)

        self.v1_button = QPushButton("Открыть клапан V1")
        self.v1_button.clicked.connect(lambda: self.toggle_valve("V1"))
        control_layout.addWidget(self.v1_button)

        self.v2_button = QPushButton("Открыть клапан V2")
        self.v2_button.clicked.connect(lambda: self.toggle_valve("V2"))
        control_layout.addWidget(self.v2_button)

        self.v3_button = QPushButton("Открыть клапан V3")
        self.v3_button.clicked.connect(lambda: self.toggle_valve("V3"))
        control_layout.addWidget(self.v3_button)

        self.v4_button = QPushButton("Открыть клапан V4")
        self.v4_button.clicked.connect(lambda: self.toggle_valve("V4"))
        control_layout.addWidget(self.v4_button)

        self.v5_button = QPushButton("Открыть клапан V5")
        self.v5_button.clicked.connect(lambda: self.toggle_valve("V5"))
        control_layout.addWidget(self.v5_button)

        self.v8_button = QPushButton("Открыть клапан V8")
        self.v8_button.clicked.connect(lambda: self.toggle_valve("V8"))
        control_layout.addWidget(self.v8_button)

        basic_panel = QWidget()
        self.work_control.addWidget(basic_panel)
        basic_layout = QVBoxLayout()
        basic_panel.setLayout(basic_layout)

        self.v10_button = QPushButton("Открыть клапан V1")
        self.v10_button.clicked.connect(lambda: self.toggle_valve("V1"))
        basic_layout.addWidget(self.v10_button)

        self.v20_button = QPushButton("Открыть клапан V2")
        self.v20_button.clicked.connect(lambda: self.toggle_valve("V2"))
        basic_layout.addWidget(self.v20_button)

        # === Block 2: Schematic Widget ===
        self.schematic = SchematicWidget()

        # === Block 3: Graph Panel with 4 Graphs ===
        self.graph_panel = GraphPanel()

        # Add blocks to main layout
        main_layout.addWidget(menubar, 0, 0)
        work_layout.addWidget(scroll_area)
        work_layout.addWidget(self.schematic, stretch=1)
        work_layout.addWidget(self.graph_panel, stretch=1)
        main_layout.addWidget(work_panel)

    def setAvto(self):
        self.work_control.setCurrentIndex(1)

    def setPro(self):
        self.work_control.setCurrentIndex(0)

    def ReadEeprom(self):
        self.w = EepromWindow()
        self.w.show()

    def ReadConfig(self):
        self.w2 = ConfigWidget()
        self.w2.show()

    def display_data(self, data):
        self.graph_panel.update_plots([data["MIDA"], data["Magdischarge"], data["ThermalIndicator"]])

    def display_error(self, error_msg):
        ...

    def update_connection_status(self, connected):
        ...

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


    def toggle_valve(self, name):
        self.schematic.toggle_valve(name)
        self.graph_panel.mark_event()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
