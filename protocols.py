class RegularExchangeProtocol:
    def __init__(self):
        self._ForVacuumState = None
        self._TMNState = None
        self._DU16 = None
        self._DU63 = None
        self._ElectroValveState = None
        self._Mode = None
        self._TMNrpm = None
        self._Magdischarge = None
        self._TEMP1 = None
        self._TEMP2 = None
        self._Analogexit = None

    # ForVacuumState
    def get_ForVacuumState(self):
        return self._ForVacuumState

    def set_ForVacuumState(self, value):
        self._ForVacuumState = value

    # TMNState
    def get_TMNState(self):
        return self._TMNState

    def set_TMNState(self, value):
        self._TMNState = value

    # DU16
    def get_DU16(self):
        return self._DU16

    def set_DU16(self, value):
        self._DU16 = value

    # DU63
    def get_DU63(self):
        return self._DU63

    def set_DU63(self, value):
        self._DU63 = value

    # ElectroValveState
    def get_ElectroValveState(self):
        return self._ElectroValveState

    def set_ElectroValveState(self, value):
        self._ElectroValveState = value

    # Mode
    def get_Mode(self):
        return self._Mode

    def set_Mode(self, value):
        self._Mode = value

    # TMNrpm
    def get_TMNrpm(self):
        return self._TMNrpm

    def set_TMNrpm(self, value):
        self._TMNrpm = value

    # Magdischarge
    def get_Magdischarge(self):
        return self._Magdischarge

    def set_Magdischarge(self, value):
        self._Magdischarge = value

    # TEMP1
    def get_TEMP1(self):
        return self._TEMP1

    def set_TEMP1(self, value):
        self._TEMP1 = value

    # TEMP2
    def get_TEMP2(self):
        return self._TEMP2

    def set_TEMP2(self, value):
        self._TEMP2 = value

    # Analogexit
    def get_Analogexit(self):
        return self._Analogexit

    def set_Analogexit(self, value):
        self._Analogexit = value

    def get_MIDA(self):
        return self._MIDA

    def set_MIDA(self, value):
        self._MIDA = value