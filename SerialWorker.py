from PyQt5.QtCore import QObject, QThread, pyqtSignal
import serial
import struct
import serial.tools.list_ports
from time import sleep

class SerialWorker(QObject):
    data_received = pyqtSignal(dict)  # Сигнал для передачи полученных данных
    error_occurred = pyqtSignal(str)  # Сигнал для ошибок
    connection_status = pyqtSignal(bool)  # Сигнал статуса подключения

    def __init__(self):
        super().__init__()
        self.port = '/dev/ttyUSB0'
        self.baudrate = 115200
        self.timeout = 1
        self.is_running = True
        self.serial_connection = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
        self.sync_byte_exchange = 0xAA
        self.sync_byte_error = 0xBB
        self.sync_byte_eprom = 0xCC

    def parse_exchange_packet(self):
        prot = {}
        len1byte = self.serial_connection.read(1)[0]
        len4byte = self.serial_connection.read(1)[0]

        if len1byte + 4 * len4byte != 34:
            return
            # raise BROKEN_POCKET

        # 1-байтные поля
        dt1byte = []
        for i in range(len1byte):
            dt1byte.append(self.serial_connection.read(1)[0])

        prot["ForVacuumState"] = dt1byte[0]
        prot["TMNState"] = dt1byte[1]
        prot["DU16"] = dt1byte[2]
        prot["DU63"] = dt1byte[3]
        prot["ElectroValveState"] = dt1byte[4]
        prot["Mode"] = dt1byte[5]

        # 4-байтные поля
        dt4byte = []
        for i in range(len4byte):
            dt4byte.append(self.serial_connection.read(4))

        prot["TMNrpm"] = int.from_bytes(dt4byte[0], 'little')
        prot["MIDA"] = struct.unpack('<f', dt4byte[1])[0]
        prot["Magdischarge"] = struct.unpack('<f', dt4byte[2])[0]
        prot["ThermalIndicator"] = struct.unpack('<f', dt4byte[3])[0]
        prot["TEMP1"] = struct.unpack('<f', dt4byte[4])[0]
        prot["TEMP2"] = struct.unpack('<f', dt4byte[5])[0]
        prot["Analogexit"] = struct.unpack('<f', dt4byte[6])[0]

        self.data_received.emit(prot)

    def parse_error_packet(self):
        prot = {}
        prot["CMD_ID"] = self.serial_connection.read(1)[0]
        prot["ERROR_CODE"] = self.serial_connection.read(1)[0]

        lenerr = self.serial_connection.read(1)[0]
        prot["ERROR_INFO"] = self.serial_connection.read(lenerr)

    def parse_eprom_packet(self):
        ...

    def connect_serial(self):
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            self.connection_status.emit(True)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Connection error: {str(e)}")
            self.connection_status.emit(False)
            return False

    def disconnect_serial(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.connection_status.emit(False)

    def read_serial_data(self):
        while self.is_running:
            try:
                # Ожидание байта синхронизации
                byte = self.serial_connection.read(1)
                if not byte:
                    continue
                if byte[0] == self.sync_byte_exchange:
                    self.parse_exchange_packet()
                elif byte[0] == self.sync_byte_error:
                    packet = byte + self.serial_connection.read(36)  # уже прочитали 1 байт, читаем оставшиеся
                    #parse_error_packet(packet)
                elif byte[0] == self.sync_byte_eprom:
                    packet = byte + self.serial_connection.read(36)  # уже прочитали 1 байт, читаем оставшиеся
                    #parse_eprom_packet(packet)
            except Exception as e:
                self.error_occurred.emit(f"Read error: {str(e)}")
                sleep(1)

    def stop(self):
        self.is_running = False
        self.disconnect_serial()