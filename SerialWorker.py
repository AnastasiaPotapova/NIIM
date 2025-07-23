from PyQt5.QtCore import QObject, pyqtSignal
import serial
import struct
from time import sleep


class SerialWorker(QObject):
    """Работает в отдельном QThread, сам пытается найти устройство,
    читает данные и сообщает о подключении/отключении."""
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(bool)      # True ‒ устройство есть, False ‒ потеряно

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200, timeout: int = 1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.sync_byte_exchange = 0xAA
        self.sync_byte_error   = 0xBB
        self.sync_byte_eprom   = 0xCC

        self.serial_connection = None
        self.is_running = True        # для корректной остановки из-вне

    # ----------  парсинг пакетов  ----------
    def parse_exchange_packet(self):
        prot = {}
        len1 = self.serial_connection.read(1)[0]
        len4 = self.serial_connection.read(1)[0]
        if len1 + 4 * len4 != 34:          # простой контроль длины
            return

        # 1-байтные
        dt1 = [self.serial_connection.read(1)[0] for _ in range(len1)]
        prot["ForVacuumState"], prot["TMNState"], prot["DU16"], prot["DU63"], \
            prot["ElectroValveState"], prot["Mode"] = dt1[:6]

        # 4-байтные
        dt4 = [self.serial_connection.read(4) for _ in range(len4)]
        fields = ["TMNrpm", "MIDA", "Magdischarge", "ThermalIndicator",
                  "TEMP1", "TEMP2", "Analogexit"]
        for name, raw in zip(fields, dt4):
            prot[name] = struct.unpack('<f', raw)[0] if name != "TMNrpm" else int.from_bytes(raw, 'little')

        self.data_received.emit(prot)

    def parse_error_packet(self):
        prot = {
            "CMD_ID":     self.serial_connection.read(1)[0],
            "ERROR_CODE": self.serial_connection.read(1)[0],
        }
        length = self.serial_connection.read(1)[0]
        prot["ERROR_INFO"] = self.serial_connection.read(length)
        self.data_received.emit(prot)

    def parse_eprom_packet(self):
        # при необходимости заполните
        pass

    # ----------  работа с портом  ----------
    def _open_port(self) -> bool:
        """Пробует открыть порт; True ‒ открылся и готов, False ‒ нет."""
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            return True
        except Exception as e:
            self.error_occurred.emit(f"Connection error: {e}")
            self.serial_connection = None
            return False

    def _close_port(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.serial_connection = None

    # ----------  главный цикл потока  ----------
    def run(self):
        """Эта функция подключается к QThread.started.
        Не блокирует GUI ‒ работает внутри потока."""
        while self.is_running:
            # 1. Пытаемся найти устройство
            while self.is_running and not self._open_port():
                sleep(1)

            if not self.is_running:
                break

            # Простейшая проверка «жив-ли контроллер» (ожидаем байт 0x01)
            try:
                if self.serial_connection.read(1) != b'\x01':
                    raise serial.SerialException("Handshake byte not received")
            except Exception as e:
                self.error_occurred.emit(str(e))
                self._close_port()
                continue

            # Устройство нашлось
            self.connection_status.emit(True)

            # 2. Читаем данные, пока порт открыт
            while self.is_running and self.serial_connection and self.serial_connection.is_open:
                try:
                    byte = self.serial_connection.read(1)
                    if not byte:
                        continue
                    if byte[0] == self.sync_byte_exchange:
                        self.parse_exchange_packet()
                    elif byte[0] == self.sync_byte_error:
                        self.parse_error_packet()
                    elif byte[0] == self.sync_byte_eprom:
                        self.parse_eprom_packet()
                except serial.SerialException as e:
                    self.error_occurred.emit(f"Read error: {e}")
                    break
                except Exception as e:
                    self.error_occurred.emit(f"Parse error: {e}")

            # 3. Если мы здесь ‒ порт пропал
            self._close_port()
            self.connection_status.emit(False)

    # ----------  остановка  ----------
    def stop(self):
        self.is_running = False
        self._close_port()