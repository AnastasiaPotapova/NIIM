from main_imports import *
from ShematicWindow import *
from GraphWindow import *

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

    def toggle_valve(self, name):
        self.schematic.toggle_valve(name)
        self.graph_panel.mark_event()

class LoadingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ожидание устройства...")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Ожидание подключения по COM..."))
        self.setLayout(layout)
        self.setGeometry(100, 100, 300, 100)

class App:
    def __init__(self):
        self.app = QApplication(sys.argv)

        self.loading = LoadingWindow()
        self.main = MainWindow()
        self.loading.show()
        self.serial_thread = None
        self.serial_worker = None
        self.display_data = None
        self.display_error = None
        self.update_connection_status = None

        self.start_serial_thread()

    def launch_main_window(self):
        self.loading.close()
        self.main.show()

    def start_serial_thread(self):
        self.serial_worker = SerialWorker()
        self.serial_thread = QThread()

        self.serial_worker.moveToThread(self.serial_thread)

        #self.serial_worker.data_received.connect(self.display_data)
        #self.serial_worker.error_occurred.connect(self.display_error)
        self.serial_worker.connection_status.connect(self.launch_main_window)

        self.serial_thread.started.connect(self.serial_worker.connect_serial)
        self.serial_thread.started.connect(self.serial_worker.read_serial_data)

        if self.update_connection_status:
            self.launch_main_window()

        self.serial_thread.start()

    def stop_serial_thread(self):
        if self.serial_worker:
            self.serial_worker.stop()
        if self.serial_thread:
            self.serial_thread.quit()
            self.serial_thread.wait()

        self.serial_worker = None
        self.serial_thread = None


    def run(self):
        sys.exit(self.app.exec_())