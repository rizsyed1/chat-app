import socket
import errno
import sys
import argparse
import threading
import logger


class Client:
    def __init__(self, IP, PORT):
        self.IP = IP
        self.PORT = PORT
        self.my_username = ''
        self.HEADER_LENGTH = 16
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.instantiated_logger = logger.Logger(__name__)
        self.logger = self.instantiated_logger.initialise_logging()

    def set_up_username(self):
        self.my_username = input("Username: ")
        username = self.my_username.encode('utf-8')
        self.client_socket.connect((self.IP, self.PORT))
        self.client_socket.setblocking(False)
        username_header = f"{len(username):<{self.HEADER_LENGTH}}".encode('utf-8')
        self.client_socket.send(username_header + username)

    def send_message(self):
        while True:
            message = input(f'{self.my_username} >')
            if message:
                message = message.encode('utf-8')
                message_header = f"{len(message):<{self.HEADER_LENGTH}}".encode('utf-8')
                self.client_socket.send(message_header + message)

    def receive_message(self):
        while True:
            try:
                username_header = self.client_socket.recv(self.HEADER_LENGTH)

                if not len(username_header):
                    sys.exit()

                username_length = int(username_header.decode('utf-8').strip())
                sender_username = self.client_socket.recv(username_length).decode('utf-8').strip()
                message_header = self.client_socket.recv(self.HEADER_LENGTH)
                message_length = int(message_header.decode('utf-8').strip())
                message = self.client_socket.recv(message_length).decode('utf-8')
                print(f'{sender_username} says {message}')

            except IOError as e:
                # This is normal on non blocking connections - when
                #  there are no incoming data, error is going to be
                # raised
                # Some operating systems will indicate that
                # using AGAIN, and some using WOULDBLOCK error code
                # We are going to check for both - if one of
                # them - that's expected, means no incoming data,
                # continue as normal
                # If we got different error code - something
                # happened
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    print('Reading error: {}'.format(str(e)))
                    sys.exit()

            except Exception as e:
                # Any other exception - something happened. Exit
                print('Reading error: {}'.format(str(e)))
                sys.exit()


parser = argparse.ArgumentParser(
    prog='chat-client',
    usage='%(prog)s [options] IP PORT',
    description='Set up the chat window')

parser.add_argument(
    'IP',
    nargs='?',
    default='127.0.0.1',
    metavar='IP-address',
    type=str,
    help='the IP address of client socket')

parser.add_argument(
    'PORT',
    nargs='?',
    default=1234,
    metavar='Port',
    type=str,
    help='the port of the client socket')

args = parser.parse_args()
client = Client(args.IP, args.PORT)
client.set_up_username()
threads = []

send_thread = threading.Thread(target=client.send_message)
send_thread.start()
threads.append(send_thread)

receive_thread = threading.Thread(target=client.receive_message)
receive_thread.start()
threads.append(receive_thread)

for thread in threads:
    thread.join()

