import socket
import errno
import sys
import argparse
import threading
import logger
import tkinter as tk


class Client:
    def __init__(self, IP, PORT):
        self.IP = IP
        self.PORT = PORT
        self.my_username = None
        self.HEADER_LENGTH = 16
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.instantiated_logger = logger.Logger(__name__)
        self.instantiated_logger.initialise_logging()
        self.username_taken_message = 'Username already taken - please enter another'
        self.username_accepted_message = 'Username assigned to you'
        self.server_disconnected_message = 'Server disconnected - please try reconnecting. sorry :('
        self.client_closed = False
        self.chat_bot_name = 'chatbot'

        """initialise tkinter gui"""
        self.window = tk.Tk()
        self.window.title('Chat')
        self.messages_frame = tk.Frame()
        self.my_msg = tk.StringVar()
        self.scrollbar = tk.Scrollbar(self.messages_frame)
        self.msg_list = tk.Listbox(self.messages_frame, height=15, width=50, yscrollcommand=self.scrollbar.set)
        self.msg_list.pack(side=tk.LEFT, fill=tk.BOTH)
        self.messages_frame.pack()
        self.entry_field = tk.Entry(self.window, textvariable=self.my_msg)
        self.entry_field.bind('<Return>', self.send_username_thread)
        self.entry_field.pack()
        self.send_button = tk.Button(self.window, text='Send', command=self.send_username_thread)
        self.send_button.pack()
        self.window.protocol('WM_DELETE_WINDOW', self.close_window)
        self.send_pressed = False

    def send_username_thread(self, event=None):
        thread = threading.Thread(target=self.send_username)
        thread.daemon = True
        thread.start()

    def receive_message_thread(self, event=None):
        receive_thread = threading.Thread(target=client.receive_message)
        receive_thread.daemon = True
        receive_thread.start()

    def send_message_thread(self, event=None):
        send_thread = threading.Thread(target=client.send_message())
        send_thread.daemon = True
        send_thread.start()

    def close_window(self, event=None):
        self.client_closed = True
        self.client_socket.close()
        self.window.quit()

    def send_username(self):
        username = self.my_msg.get()
        while username and self.my_username is None:
            try:
                encoded_username = username.encode('utf-8')
                username_header = f'{len(encoded_username):<{self.HEADER_LENGTH}}'.encode('utf-8')
                self.client_socket.send(username_header + encoded_username)
                response_header = self.client_socket.recv(self.HEADER_LENGTH)

                if not len(response_header):
                    sys.exit()

                response_length = int(response_header.decode('utf-8').strip())
                response_message = self.client_socket.recv(response_length).decode('utf-8').strip()

                if response_message == self.username_taken_message:
                    self.msg_list.insert(tk.END, self.username_taken_message)
                elif response_message == self.username_accepted_message:
                    self.msg_list.insert(tk.END, self.username_accepted_message)
                    self.my_username = encoded_username.decode('utf-8')
                    self.send_button.configure(text='Send', command=self.send_message_thread)
                    self.entry_field.bind('<Return>', self.send_message_thread)
                    self.receive_message_thread()
                else:
                    self.msg_list.insert(
                        tk.END, f'{self.chat_bot_name} > Error: {response_message} re-enter username please'
                    )

                self.my_msg.set('')
                return


            except IOError as e:
                """When there is no incoming data, error is going to be raised. Some operating systems will 
                indicate using EGAIN, some EWOULDBLOCK.We check for both - if one of them - that's
                expected, means no incoming data, continue as normal. If we got different error code - something 
                happened"""
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    self.msg_list.insert(tk.END, f'{self.chat_bot_name} > Error -  {str(e)}')
                    sys.exit()

                """Did not receive anything"""
                continue

            except Exception as e:
                """ Any other exception - something happened. Exit"""
                self.msg_list.insert(tk.END, f'{self.chat_bot_name} > Reading error: {str(e)}')
                sys.exit()


    def send_message(self):
        message = self.my_msg.get()
        self.msg_list.insert(tk.END, f'{self.my_username} > {message}')
        self.my_msg.set('')
        if message:
            message = message.encode('utf-8')
            message_header = f'{len(message):<{self.HEADER_LENGTH}}'.encode('utf-8')
            self.client_socket.send(message_header + message)
        return

    def receive_message(self):
        while True:
            if not self.client_closed and self.my_username:
                try:
                    username_header = self.client_socket.recv(self.HEADER_LENGTH)
                    if not len(username_header):
                        self.msg_list.insert( tk.END, f'{self.chat_bot_name} > {self.server_disconnected_message}')
                        sys.exit()

                    username_length = int(username_header.decode('utf-8').strip())
                    sender_username = self.client_socket.recv(username_length).decode('utf-8').strip()
                    message_header = self.client_socket.recv(self.HEADER_LENGTH)
                    message_length = int(message_header.decode('utf-8').strip())
                    message = self.client_socket.recv(message_length).decode('utf-8')
                    self.client_socket.setblocking(False)
                    self.msg_list.insert(tk.END, f'{sender_username} > {message}')

                except IOError as e:
                    """When there is no incoming data, error is going to be raised. Some operating systems will 
                    indicate using EGAIN, some EWOULDBLOCK.We check for both - if one of them - that's
                    expected, means no incoming data, continue as normal. If we got different error code - something 
                    happened"""
                    if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                        self.instantiated_logger.logger.info('Reading error: {}'.format(str(e)))

                    """Client did not receive anything"""
                    continue

                except Exception as e:
                    """Something happened. Exit"""
                    self.msg_list.insert( tk.END, f'{self.chat_bot_name} > {self.server_disconnected_message}')
                    self.instantiated_logger.logger.info('Reading error: {}'.format(str(e)))
                    sys.exit()

            if self.client_closed:
                return


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
client.client_socket.connect((client.IP, client.PORT))


client.msg_list.insert(
    tk.END, f'{client.chat_bot_name} > Please enter your username'
)

tk.mainloop()








