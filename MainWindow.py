from PyQt5.QtCore import QThread
from main_imports import *
from ShematicWindow import *
from GraphWindow import *
from SerialWorker import SerialWorker


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

    @pyqtSlot(list)
    def handle_data(self, data_list: list):
        self.table.setRowCount(len(data_list))
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Индекс", "0x", "dec"])

        for i, val in enumerate(data_list):
            self.table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.table.setItem(i, 1, QTableWidgetItem(hex(val)))
            self.table.setItem(i, 2, QTableWidgetItem(str(val)))

    def read_eeprom_command(self):
        try:
            start = int(self.start_input.text())
            end = int(self.end_input.text())
            if start > end:
                raise ValueError("Начальный индекс должен быть меньше или равен конечному.")
        except ValueError:
            logging.error("Необходимо ввести числа")
            self.start_input.setText("")
            self.end_input.setText("")
            self.start_input.setPlaceholderText("Ошибка: введите числа")
            self.end_input.setPlaceholderText("Ошибка: введите числа")
            return

        count = end - start + 1
        cmd_id = 0x11  # команда чтения EEPROM
        address = start
        num_bytes = bytes([count])
        self.send_eprom_command_signal.emit(cmd_id, address, num_bytes)


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
    send_command_signal = pyqtSignal(int, bytes)
    send_eprom_command_signal = pyqtSignal(int, int, bytes)
    eeprom_data_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCADA NIIM")
        self.setGeometry(100, 100, 1280, 1024)
        self.setup_ui()
        self.mode = 0
        self.error_box_open = False

    # ----------  UI  ----------
    def setup_ui(self):
        main_layout = QGridLayout()
        work_panel  = QWidget()
        work_layout = QHBoxLayout()
        work_panel.setLayout(work_layout)
        self.setLayout(main_layout)

        menubar = QMenuBar()
        actionFile = menubar.addMenu("Режим работы")
        actionFile.addAction("Автоматический").triggered.connect(self.setAvto)
        actionFile.addAction("Продвинутый").triggered.connect(self.setPro)

        eeprom_menu = menubar.addMenu("ЭСППЗУ")
        eeprom_menu.addAction("Записать")
        eeprom_menu.addAction("Прочитать").triggered.connect(self.ReadEeprom)

        menubar.addAction("Редактировать конфигурацию").triggered.connect(self.ReadConfig)
        menubar.addMenu("Логи")

        #  ---  панель управления  ---
        self.work_control = QStackedWidget()
        control_panel     = QWidget()
        control_layout    = QVBoxLayout(control_panel)
        self.work_control.addWidget(control_panel)   # продвинутый
        basic_panel = QWidget()
        basic_layout = QVBoxLayout(basic_panel)
        self.work_control.addWidget(basic_panel)     # автоматический

        # продвинутые клапаны
        for name in ("V1", "V2", "V3", "V4", "V5", "V8"):
            btn = QPushButton(f"Открыть клапан {name}")
            btn.clicked.connect(lambda _, n=name: self.toggle_valve(n))
            control_layout.addWidget(btn)

        # упрощённая панель
        for name in ("V1", "V2"):
            btn = QPushButton(f"Открыть клапан {name}")
            btn.clicked.connect(lambda _, n=name: self.toggle_valve(n))
            basic_layout.addWidget(btn)

        scroll = QScrollArea()
        scroll.setWidget(self.work_control)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(200)

        # схематика и графики
        self.schematic   = SchematicWidget()
        self.graph_panel = GraphPanel()

        # финальное размещение
        main_layout.addWidget(menubar, 0, 0)
        work_layout.addWidget(scroll)
        work_layout.addWidget(self.schematic, stretch=1)
        work_layout.addWidget(self.graph_panel, stretch=1)
        main_layout.addWidget(work_panel)

    # ----------  меню режимов  ----------
    def setAvto(self): self.work_control.setCurrentIndex(1)
    def setPro(self):  self.work_control.setCurrentIndex(0)

    # ----------  дополнительные окна  ----------
    def ReadEeprom(self):
        self.w = EepromWindow()
        self.w.send_eprom_command_signal.connect(self.send_eprom_command_signal)
        self.eeprom_data_signal.connect(self.w.handle_data)
        self.w.show()

    def ReadConfig(self):
        self.w2 = ConfigWidget(); self.w2.show()

    # ----------  обратные вызовы от SerialWorker  ----------
    def display_data(self, data: dict):
        if "EEPROM_READ" in data:
            self.eeprom_data_signal.emit(data["EEPROM_READ"])
            return


        # Пример ‒ обновляем графики
        self.graph_panel.update_plots([data.get("MIDA", 0),
                                       data.get("Magdischarge", 0),
                                       data.get("ThermalIndicator", 0)])

    def display_error(self, msg: str):
        if self.error_box_open:
            return  # Уже показывается окно — не дублируем

        self.error_box_open = True

        box = QMessageBox(self)
        box.setWindowTitle("Ошибка связи")
        box.setText(msg)
        box.setIcon(QMessageBox.Critical)
        box.setStandardButtons(QMessageBox.Ok)

        # Сброс флага, когда окно закрывается
        box.buttonClicked.connect(lambda _: setattr(self, 'error_box_open', False))
        logging.error("Ошибка связи: " + msg)
        box.show()

    def update_connection_status(self, connected: bool):
        postfix = " (подключено)" if connected else " (нет подключения)"
        self.setWindowTitle("UdavProg" + postfix)

    # ----------  пользовательские действия  ----------
    def toggle_valve(self, name: str):
        self.graph_panel.mark_event()

        valve_id = {
            "V1": 1,
            "V2": 2,
            "V3": 3,
            "V4": 4,
            "V5": 5,
            "V8": 8
        }.get(name, 0)

        if valve_id:
            cmd_id = 0x01
            payload = bytes([valve_id])
            self.send_command_signal.emit(cmd_id, payload)

# ------------------------------------------------------------------------------------------------
#                                          Приложение
# ------------------------------------------------------------------------------------------------
class LoadingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ожидание устройства...")
        self.setGeometry(100, 100, 300, 100)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Ожидание подключения по COM..."))


class App:
    def __init__(self):
        self.qt_app = QApplication(sys.argv)

        # окно ожидания (может быстро исчезнуть, если контроллер уже подключён)
        self.loading = LoadingWindow()
        self.loading.show()

        # создаём поток + воркера
        self.serial_thread = QThread()
        self.serial_worker = SerialWorker()
        self.serial_worker.moveToThread(self.serial_thread)

        # сигналы
        self.serial_thread.started.connect(self.serial_worker.run_input)
        self.serial_worker.connection_status.connect(self._on_connection_status)

        self.serial_thread.start()
        self.main: MainWindow | None = None

    # ----------  реакции на (от-)подключение устройства  ----------
    def _on_connection_status(self, connected: bool):
        if connected:
            # если главное окно ещё не создано – создаём
            if self.main is None:
                self._launch_main_window()
            else:
                self.main.update_connection_status(True)

            # убираем окно ожидания
            if self.loading.isVisible():
                self.loading.hide()
        else:
            # устройство исчезло
            if self.main:
                self.main.update_connection_status(False)
            if not self.loading.isVisible():
                self.loading.show()

    def _launch_main_window(self):
        self.main = MainWindow()

        # перенаправляем сигналы сразу в интерфейс
        self.serial_worker.data_received.connect(self.main.display_data)
        self.serial_worker.error_occurred.connect(self.main.display_error)
        self.serial_worker.connection_status.connect(self.main.update_connection_status)

        self.main.show()

    # ----------  корректное закрытие  ----------
    def _stop_serial_thread(self):
        if self.serial_worker:
            self.serial_worker.stop()
        if self.serial_thread:
            self.serial_thread.quit()
            self.serial_thread.wait()

    def run(self):
        exit_code = self.qt_app.exec_()
        self._stop_serial_thread()
        sys.exit(exit_code)


# ------------------------------  точка входа  ------------------------------
if __name__ == "__main__":
    App().run()