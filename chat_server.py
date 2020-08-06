import server_socket
import argparse
import logger
import psycopg2
import psycopg2.errors
from psycopg2 import sql
import select
import errno


class Server:
    def __init__(self, IP, PORT):
        self.server_socket = server_socket.Socket(IP, PORT)
        self.clients = {}
        self.sockets_list = [self.server_socket]
        self.HEADER_LENGTH = 16
        self.instantiated_logger = logger.Logger(__name__)
        self.instantiated_logger.initialise_logging()
        self.root_database_connection = psycopg2.connect(
            dbname='postgres', user='rizwan', host='localhost', password='password123'
        )
        self.dbname = 'chatdb'
        self.client_socket_usernames_accepted = []

    def remove_client(self, db_connection, socket):
        username = self.clients[socket]['data'].decode('utf-8')
        try:
            self.instantiated_logger.logger.info(
                'Closed connection from: {}'.format(username)
            )

            self.sockets_list.remove(socket)

            del self.clients[socket]

            cur = db_connection.cursor()

            cur.execute(
                """
                    DELETE FROM
                        usernames
                    WHERE
                        username=%(username)s
                """, {
                        'username': username
                    })

        except Exception as e:
            self.instantiated_logger.logger.exception(e)

    def add_client(self, client_name, socket, client_address):
        self.instantiated_logger.logger.info("Added client {}:{}, name: {}".format(
            *client_address, client_name['data'].decode('utf-8'))
        )

        self.clients[socket] = client_name

    def read_message(self, socket_client):
        try:
            message_header = socket_client.recv(self.HEADER_LENGTH)

            """If socket closed by client, or as soon as client used shutdown"""
            if len(message_header) == 0:
                return False

            message_length = int(message_header.decode('utf-8').strip())
            message = socket_client.recv(message_length)
            return {'header': message_header, 'data': message}

        except Exception as e:
            """Any other exception - something happened. Exit"""
            return False

    def broadcast_messages(self, read_socket, message):
        for client in self.clients:
            if client != read_socket:
                sender_client = self.clients[read_socket]
                client.send(sender_client['header'] + sender_client['data']
                            + message['header'] + message['data'])

    def create_username_database(self):
        """Creates database and table of usernames"""

        """Create database"""
        dbname = self.dbname
        self.root_database_connection.set_session(readonly=False, autocommit=True)
        cur = self.root_database_connection.cursor()
        cur.execute("DROP DATABASE IF EXISTS " + dbname)
        cur.execute('CREATE DATABASE ' + dbname)
        cur.close()
        self.root_database_connection.close()

        """Connect to created database"""
        conn = psycopg2.connect(dbname=dbname, user='rizwan', host='localhost', password='password123')

        """Create a table of usernames"""
        cur = conn.cursor()
        cur.execute('CREATE TABLE usernames(username varchar(30))')
        conn.commit()
        cur.close()
        return conn


parser = argparse.ArgumentParser(
    prog='chat-server',
    usage='%(prog)s [options] IP PORT',
    description='Set up the chat window'
)

parser.add_argument(
    'IP',
    nargs='?',
    default='',
    metavar='IP-address',
    type=str,
    help='the IP address of client socket'
)

parser.add_argument(
    'PORT',
    nargs='?',
    default=1234,
    metavar='Port',
    type=str,
    help='the port of the client socket'
)


def reject_username(reject_message, server, client_socket):
    reject_message = reject_message.encode('utf-8')
    reject_message_header = f'{len(reject_message):<{server.HEADER_LENGTH}}'.encode('utf-8')
    client_socket.send(reject_message_header + reject_message)


def store_username(db_connection, client_socket, username, server):
    if len(username) < 2 or len(username) > 32:
        reject_username('username should be between 2 and 31 characters long - try again', server, client_socket)
        return False

    banned_chars = "@#:`'\""
    for char in username:
        if char in banned_chars:
            reject_username(
                'username contains invalid characters - try again ("@", "#", ":" and all quotation marks not accepted)',
                server, client_socket)
            return False

    cur = db_connection.cursor()

    cur.execute("""
        SELECT 
            username 
        FROM 
            usernames 
        WHERE 
            username=%(username)s
    """, {
        'username': username
    })

    row = cur.fetchone()

    if row is None:
        cur.execute("""
        INSERT INTO 
            usernames (username) 
        VALUES 
            (%(username)s)
    """, {
            'username': username
        })

        db_connection.commit()
        accept_username_message = 'Username assigned to you'.encode('utf-8')
        accept_username_message_header = f'{len(accept_username_message):<{server.HEADER_LENGTH}}'.encode('utf-8')
        client_socket.send(accept_username_message_header + accept_username_message)
        return username.encode('utf-8')
    else:
        reject_username('Username already taken - please enter another', server, client_socket)
        return False


def accept_username(db_connection, socket, server):
    client_name = server.read_message(socket)

    if client_name is False:
        return False

    username = client_name['data'].decode('utf-8')
    accepted_username = store_username(db_connection, socket, username, server)

    if not accepted_username:
        return False

    server.client_socket_usernames_accepted.append(socket)

    server.add_client(client_name, socket, socket.getpeername())

    return True


if __name__ == '__main__':
    args = parser.parse_args()
    server = Server(args.IP, args.PORT)
    db_connection = server.create_username_database()

    while True:
        read_sockets, _, exception_sockets = select.select(server.sockets_list, [], server.sockets_list)
        for socket in read_sockets:
            if socket == server.server_socket:
                try:
                    client_socket, client_address = server.server_socket.accept()
                    client_socket.setblocking(False)
                    server.sockets_list.append(client_socket)
                    username_accepted = accept_username(db_connection, client_socket, server)

                    if not username_accepted:
                        continue

                except IOError as e:
                    """When there is no incoming data, error is going to be raised. Some operating systems will 
                    indicate using EGAIN, some EWOULDBLOCK.We check for both - if one of them - that's
                    expected, means no incoming data, continue as normal. If we got different error code - something 
                    happened"""

                    if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                        server.instantiated_logger.logger.info('Reading error: {}'.format(str(e)))
                    """Server  did not receive anything"""
                    continue

                except Exception as e:
                    """ Any other exception - something happened."""
                    server.instantiated_logger.logger.info('Reading error: {}'.format(str(e)))

            else:

                if socket not in server.client_socket_usernames_accepted:
                    username_accepted = accept_username(db_connection, socket, server)

                    if not username_accepted:
                        continue

                else:
                    message = None

                    try:
                        message = server.read_message(socket)

                    except IOError as e:
                        """When there is no incoming data, error is going to be raised. Some operating systems will 
                        indicate using EGAIN, some EWOULDBLOCK.We check for both - if one of them - that's
                        expected, means no incoming data, continue as normal. If we got different error code - something 
                        happened"""
                        if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                            server.instantiated_logger.logger.info('Reading error: {}'.format(str(e)))
                        """Server did not receive anything"""
                        continue

                    except Exception as e:
                        """ Any other exception - something happened."""
                        server.instantiated_logger.logger.info('Reading error: {}'.format(str(e)))

                    if socket in server.clients:
                        if message is False:
                            server.remove_client(db_connection, socket)
                            continue

                        server.instantiated_logger.logger.info(
                            f'Received message from {server.clients[socket]["data"].decode("utf-8")}:'
                            f' {message["data"].decode("utf-8")}'
                        )

                        server.broadcast_messages(socket, message)


        for notified_socket in exception_sockets:
            server.sockets_list.remove(notified_socket)
            del server.clients[notified_socket]













