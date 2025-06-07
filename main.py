import struct
import serial
from protocols import *

import struct
import serial
from protocols import *


def parse_packet(packet: bytes):
    prot = RegularExchangeProtocol()

    len1byte = int.from_bytes(packet[1], 'little')
    len4byte = int.from_bytes(packet[2], 'little')

    # 1-байтные поля
    dt1byte = []
    for i in range(len1byte):
        dt1byte.append(packet[3 + i])

    prot.set_ForVacuumState(dt1byte[0])
    prot.set_TMNState(dt1byte[1])
    prot.set_DU16(dt1byte[2])
    prot.set_DU63(dt1byte[3])
    prot.set_ElectroValveState(dt1byte[4])
    prot.set_Mode(dt1byte[5])

    # 4-байтные поля
    dt4byte = []
    for i in range(len4byte):
        dt4byte.append(packet[3 + len1byte + i * 4: 3 + len1byte + i * 4 + 4])

    prot.set_TMNrpm(int.from_bytes(dt4byte[0], 'little'))
    prot.set_MIDA(struct.unpack('<f', dt4byte[1])[0])
    prot.set_Magdischarge(struct.unpack('<f', dt4byte[2])[0])
    prot.set_TEMP1(struct.unpack('<f', dt4byte[3])[0])
    prot.set_TEMP2(struct.unpack('<f', dt4byte[4])[0])
    prot.set_Analogexit(struct.unpack('<f', dt4byte[5])[0])


def main():
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    sync_byte = 0xAA

    while True:
        # Ожидание байта синхронизации
        byte = ser.read(1)
        if not byte:
            continue

        if byte[0] == sync_byte:
            packet = byte + ser.read(32)  # уже прочитали 1 байт, читаем оставшиеся
            parse_packet(packet)

if __name__ == "__main__":
    main()
