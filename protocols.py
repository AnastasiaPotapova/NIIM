import struct
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo


class SerialProtocol(QObject):
    telemetry_received = pyqtSignal(dict)
    error_received = pyqtSignal(dict)
    eeprom_data_received = pyqtSignal(dict)

    def __init__(self, port_name="/dev/ttyUSB0", baud_rate=115200):
        super().__init__()
        self.serial = QSerialPort()
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.buffer = bytearray()

        # Настройка последовательного порта
        self.serial.setPortName(self.port_name)
        self.serial.setBaudRate(self.baud_rate)
        self.serial.setDataBits(QSerialPort.Data8)
        self.serial.setParity(QSerialPort.NoParity)
        self.serial.setStopBits(QSerialPort.OneStop)
        self.serial.setFlowControl(QSerialPort.NoFlowControl)

        # Подключаем сигналы
        self.serial.readyRead.connect(self._handle_data)
        self.serial.errorOccurred.connect(self._handle_error)

    def open_connection(self):
        """Открытие соединения с устройством"""
        if not self.serial.open(QSerialPort.ReadWrite):
            error = f"Ошибка открытия порта {self.port_name}: {self.serial.errorString()}"
            self.error_received.emit({
                'type': 'port_error',
                'message': error
            })
            return False
        return True

    def close_connection(self):
        """Закрытие соединения"""
        if self.serial.isOpen():
            self.serial.close()

    def send_command(self, cmd_id, payload=None):
        """
        Отправка команды управления
        Формат пакета: [HEADER:1][CMD_ID:1][PAYLOAD_LEN:1][PAYLOAD:N]
        """
        if not self.serial.isOpen():
            self.error_received.emit({
                'type': 'port_error',
                'message': "Порт не открыт"
            })
            return False

        header = 0xAA.to_bytes(1, 'little')
        cmd = cmd_id.to_bytes(1, 'little')
        payload = payload or b''
        length = len(payload).to_bytes(1, 'little')
        packet = header + cmd + length + payload

        written = self.serial.write(packet)
        if written != len(packet):
            self.error_received.emit({
                'type': 'write_error',
                'message': f"Ошибка отправки данных. Отправлено {written} из {len(packet)} байт"
            })
            return False
        return True

    def read_eeprom(self, address, num_bytes):
        """
        Чтение из EEPROM
        Формат пакета: [HEADER:1][CMD_ID:1][ADDRESS:1][NUM_BYTES:1]
        """
        header = 0xCC.to_bytes(1, 'little')
        cmd = 0x11.to_bytes(1, 'little')
        addr = address.to_bytes(1, 'little')
        num = num_bytes.to_bytes(1, 'little')
        packet = header + cmd + addr + num

        self.serial.write(packet)

    def write_eeprom(self, address, data):
        """
        Запись в EEPROM
        Формат пакета: [HEADER:1][CMD_ID:1][LENGTH:1][ADDRESS:1][DATA:N]
        """
        header = 0xCC.to_bytes(1, 'little')
        cmd = 0x10.to_bytes(1, 'little')
        length = len(data).to_bytes(1, 'little')
        addr = address.to_bytes(1, 'little')
        packet = header + cmd + length + addr + data

        self.serial.write(packet)

    def _handle_data(self):
        """Обработка входящих данных"""
        while self.serial.bytesAvailable():
            data = self.serial.readAll()
            self.buffer.extend(data.data())

            # Обрабатываем все полные пакеты в буфере
            while len(self.buffer) > 0:
                header = self.buffer[0]

                # Телеметрия (37 байт)
                if header == 0xAA and len(self.buffer) >= 37:
                    packet = bytes(self.buffer[:37])
                    self._process_telemetry(packet)
                    self.buffer = self.buffer[37:]

                # Ошибка (минимум 4 байта)
                elif header == 0xBB and len(self.buffer) >= 4:
                    info_len = self.buffer[3]
                    if len(self.buffer) >= 4 + info_len:
                        packet = bytes(self.buffer[:4 + info_len])
                        self._process_error(packet)
                        self.buffer = self.buffer[4 + info_len:]

                # EEPROM ответ
                elif header == 0xCC and len(self.buffer) >= 3:
                    cmd_id = self.buffer[1]
                    if cmd_id == 0x11:  # Ответ на чтение
                        data_len = self.buffer[2]
                        if len(self.buffer) >= 3 + data_len:
                            packet = bytes(self.buffer[:3 + data_len])
                            self._process_eeprom_response(packet)
                            self.buffer = self.buffer[3 + data_len:]
                    else:
                        self.buffer.pop(0)  # Удаляем невалидный байт

                else:
                    break  # Ждем больше данных

    def _process_telemetry(self, data):
        """Разбор пакета телеметрии"""
        try:
            # Формат: 3 байта заголовка + 8 однобайтных + 8 float (4 байта каждый)
            fmt = '<BBB8B8f'
            unpacked = struct.unpack(fmt, data[:37])

            telemetry = {
                'prefix': unpacked[0],
                'num_1byte': unpacked[1],
                'num_4byte': unpacked[2],
                'pump_status': unpacked[3],
                'tmn_status': unpacked[4],
                'valve_du16': unpacked[5],
                'valve_du63': unpacked[6],
                'valve_electric': unpacked[7],
                'work_mode': unpacked[8],
                'tmn_speed': unpacked[9],
                'mid_pressure': unpacked[10],
                'mag_pressure': unpacked[11],
                'thermo_pressure': unpacked[12],
                'temp_ch1': unpacked[13],
                'temp_ch2': unpacked[14],
                'analog_input': unpacked[15]
            }

            self.telemetry_received.emit(telemetry)

        except struct.error as e:
            self.error_received.emit({
                'type': 'parse_error',
                'message': f"Ошибка разбора телеметрии: {str(e)}"
            })

    def _process_error(self, data):
        """Разбор пакета ошибки"""
        try:
            cmd_id = data[1]
            error_code = data[2]
            info_len = data[3]
            error_info = data[4:4 + info_len].decode('ascii', 'ignore')

            error_messages = {
                0x01: "Unknown command",
                0x02: "Invalid payload length",
                0x03: "Invalid argument",
                0x04: "Device malfunction",
                0x05: "Sensor disconnected",
                0x06: "Overheat",
                0x07: "Calibration error",
                0x08: "Command not allowed in state"
            }

            self.error_received.emit({
                'type': 'device_error',
                'cmd_id': cmd_id,
                'code': error_code,
                'message': error_messages.get(error_code, "Unknown error"),
                'info': error_info
            })

        except Exception as e:
            self.error_received.emit({
                'type': 'parse_error',
                'message': f"Ошибка разбора пакета ошибки: {str(e)}"
            })

    def _process_eeprom_response(self, data):
        """Разбор ответа от EEPROM"""
        try:
            cmd_id = data[1]
            length = data[2]
            eeprom_data = data[3:3 + length]

            self.eeprom_data_received.emit({
                'cmd_id': cmd_id,
                'address': data[3] if len(data) > 3 else None,
                'data': eeprom_data
            })

        except Exception as e:
            self.error_received.emit({
                'type': 'parse_error',
                'message': f"Ошибка разбора EEPROM ответа: {str(e)}"
            })

    def _handle_error(self, error):
        """Обработка ошибок порта"""
        if error == QSerialPort.NoError:
            return

        error_messages = {
            QSerialPort.DeviceNotFoundError: "Устройство не найдено",
            QSerialPort.PermissionError: "Нет доступа к устройству",
            QSerialPort.OpenError: "Ошибка открытия устройства",
            QSerialPort.WriteError: "Ошибка записи",
            QSerialPort.ReadError: "Ошибка чтения",
            QSerialPort.ResourceError: "Устройство отключено",
            QSerialPort.UnsupportedOperationError: "Неподдерживаемая операция",
            QSerialPort.TimeoutError: "Таймаут операции",
            QSerialPort.NotOpenError: "Устройство не открыто"
        }

        message = error_messages.get(error, f"Неизвестная ошибка: {error}")
        self.error_received.emit({
            'type': 'port_error',
            'message': message
        })