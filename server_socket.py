import socket


class Socket(socket.socket):
    def __init__(self, IP, PORT):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind((IP, PORT))
        self.listen()
