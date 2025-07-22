from main_imports import *

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

