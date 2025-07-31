from main_imports import *

class SerialWorker(QObject):
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
        self.is_running = True    # для корректной остановки из-вне

        self.outgoing_buffer = Queue()

    @pyqtSlot(int, bytes)
    def handle_command(self, cmd_id: int, payload: bytes = b''):
        self.outgoing_buffer.put([cmd_id, payload])
        self.run_output()

    @pyqtSlot(int, int, bytes)
    def handle_eprom_command(self, command_id: int, address: int, data: bytes = b''):
        self.outgoing_buffer.put([command_id, address, data])
        self.run_output()

    # ----------  парсинг пакетов  ----------
    def parse_exchange_packet(self):
        prot = {}
        len1 = self.serial_connection.read(1)[0]
        len4 = self.serial_connection.read(1)[0]
        if len1 + 4 * len4 != 29:          # простой контроль длины
            return
        # 1-байтные
        dt1 = [self.serial_connection.read(1)[0] for _ in range(len1)]
        prot["ForVacuumState"], prot["TMNState"], prot["DU16"], prot["DU63"], \
            prot["ElectroValveState"] = dt1[:len1]

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
        try:
            cmd_id = self.serial_connection.read(1)[0]
            if cmd_id != 0x12:
                #self.error_occurred.emit(f"Неизвестный CMD_ID в EEPROM пакете: {cmd_id}")
                return

            length = self.serial_connection.read(1)[0]
            data = self.serial_connection.read(length)

            if len(data) != length:
                self.error_occurred.emit("Неверная длина данных в EEPROM пакете")
                return

            # преобразуем в список int
            data_list = list(data)

            # можно послать в отдельный сигнал, если хочешь разделить
            self.data_received.emit({
                "EEPROM_READ": data_list
            })
            
        except Exception as e:
            logging.error(f"Ошибка разбора EEPROM пакета: {e}")
            self.error_occurred.emit(f"Ошибка разбора EEPROM пакета: {e}")

    def send_command(self, cmd_id: int, payload: bytes = b''):
        if not self.serial_connection or not self.serial_connection.is_open:
            self.error_occurred.emit("Порт не открыт — команда не отправлена")
            return

        try:
            header = bytes([0xAA])
            cmd = bytes([cmd_id])
            payload_len = bytes([len(payload)])
            packet = header + cmd + payload_len + payload
            self.serial_connection.write(packet)
        except Exception as e:
            logging.error(f"Ошибка отправки команды: {e}")
            self.error_occurred.emit(f"Ошибка отправки команды: {e}")

    def send_eprom_command(self, command_id: int, address: int, data: bytes = b''):
        if not self.serial_connection or not self.serial_connection.is_open:
            self.error_occurred.emit("Порт не открыт — команда к EEPROM не отправлена")
            return

        try:
            header = bytes([0xCC])
            cmd = bytes([command_id])
            addr = struct.pack('<H', address)

            if command_id == 0x10:  # запись
                length = bytes([2 + len(data)])  # 2 байта адрес + данные
                packet = header + cmd + length + addr + data
            elif command_id == 0x11:  # чтение
                num_bytes = bytes([len(data)]) if data else b'\x01'  # по умолчанию читаем 1 байт
                packet = header + cmd + addr + num_bytes
            else:
                self.error_occurred.emit("Неизвестная команда для EEPROM")
                return

            self.serial_connection.write(packet)
        except Exception as e:
            logging.error(f"Ошибка отправки команды: {e}")
            self.error_occurred.emit(f"Ошибка отправки EEPROM-команды: {e}")

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
            logging.error(f"Connection error: {e}")
            self.error_occurred.emit(f"Connection error: {e}")
            self.serial_connection = None
            return False

    def _close_port(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.serial_connection = None

    # ----------  главный цикл потока  ----------
    def run_input(self):
        while self.is_running:
            # 1. Пытаемся найти устройство
            while self.is_running and not self._open_port():
                sleep(1)

            if not self.is_running:
                break
            b = self.serial_connection.read(1)
            try:
                if b != b'\xAA':
                    raise serial.SerialException("Handshake byte not received")
            except Exception as e:
                logging.error(f"Connection error: {e}")
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
                    else:
                        continue
                except serial.SerialException as e:
                    self.error_occurred.emit(f"Read error: {e}")
                    logging.error(f"Read error: {e}")
                    break
                except Exception as e:
                    self.error_occurred.emit(f"Parse error: {e}")
                    logging.error(f"Parse error: {e}")

            # 3. Если мы здесь ‒ порт пропал
            self._close_port()
            self.connection_status.emit(False)

    def run_output(self):
        while not self.outgoing_buffer.empty():
            try:
                dt = self.outgoing_buffer.get()
                if len(dt) == 2:
                    self.send_command(dt[0], dt[1])
                elif len(dt) == 3:
                    self.send_eprom_command(dt[0], dt[1], dt[2])

            except Exception as e:
                self.error_occurred.emit(f"Ошибка при сборке/отправке команды: {e}")
                logging.error(f"Ошибка при сборке/отправке команды: {e}")

    # ----------  остановка  ----------
    def stop(self):
        self.is_running = False
        self._close_port()