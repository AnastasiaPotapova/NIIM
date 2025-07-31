from queue import Queue

class CommandBuffer:
    def __init__(self):
        self.outgoing = Queue()

    def add(self, command: str):
        """Добавить команду в буфер на отправку"""
        self.outgoing.put(command)

    def get_next(self):
        """Получить следующую команду на отправку"""
        if not self.outgoing.empty():
            return self.outgoing.get()
        return None