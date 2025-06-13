import struct
import serial
from errors import *

data = []


def parse_exchange_packet(ser):
    prot = {}

    len1byte = ser.read(1)[0]
    len4byte = ser.read(1)[0]

    if len1byte + 4 * len4byte != 34:
        return
        # raise BROKEN_POCKET

    # 1-байтные поля
    dt1byte = []
    for i in range(len1byte):
        dt1byte.append(ser.read(1)[0])

    prot["ForVacuumState"] = dt1byte[0]
    prot["TMNState"] = dt1byte[1]
    prot["DU16"] = dt1byte[2]
    prot["DU63"] = dt1byte[3]
    prot["ElectroValveState"] = dt1byte[4]
    prot["Mode"] = dt1byte[5]

    # 4-байтные поля
    dt4byte = []
    for i in range(len4byte):
        dt4byte.append(ser.read(4))
    print(dt4byte)
    prot["TMNrpm"] = int.from_bytes(dt4byte[0], 'little')
    prot["MIDA"] = struct.unpack('<f', dt4byte[1])[0]
    prot["Magdischarge"] = struct.unpack('<f', dt4byte[2])[0]
    prot["ThermalIndicator"] = struct.unpack('<f', dt4byte[3])[0]
    prot["TEMP1"] = struct.unpack('<f', dt4byte[4])[0]
    prot["TEMP2"] = struct.unpack('<f', dt4byte[5])[0]
    prot["Analogexit"] = struct.unpack('<f', dt4byte[6])[0]

    print(prot)

def parse_error_packet(packet: bytes):
    ...

def parse_eprom_packet(packet: bytes):
    ...

def mai():
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    sync_byte_exchange = 0xAA
    sync_byte_error = 0xBB
    sync_byte_eprom = 0xCC


    while True:
        # Ожидание байта синхронизации
        byte = ser.read(1)
        if not byte:
            continue

        if byte[0] == sync_byte_exchange:
            #packet = byte + ser.read(36)  # уже прочитали 1 байт, читаем оставшиеся
            parse_exchange_packet(ser)
        elif byte[0] == sync_byte_error:
            packet = byte + ser.read(36)  # уже прочитали 1 байт, читаем оставшиеся
            parse_error_packet(packet)
        elif byte[0] == sync_byte_eprom:
            packet = byte + ser.read(36)  # уже прочитали 1 байт, читаем оставшиеся
            parse_eprom_packet(packet)


def get_params():
    if len(data) > 0:
        return [data[-1].get_MIDA(), data[-1].get_Magdischarge(), data[-1].get_ThermalIndicator()]
    return [0, 0, 0]

if __name__ == "__main__":
    mai()
