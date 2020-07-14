import chat_server
import pytest
import socket
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE, ISOLATION_LEVEL_AUTOCOMMIT
import psycopg2.errors


HEADER_LENGTH = 16


def add_client(server):
    client_socket, client_address = server.current_socket.accept()
    client_name = server.read_message(client_socket)
    server.add_client(client_name, client_socket)
    return client_socket

def set_and_send_username(username):
    username = username.encode('utf-8')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 1234))
    # s.setblocking(False)
    username_header = f'{len(username):<{HEADER_LENGTH}}'.encode('utf-8')
    s.send(username_header + username)
    return s


def create_username_database():
    """Create database"""
    conn = psycopg2.connect(dbname='postgres', user='rizwan', host='localhost', password='password123')
    dbname = 'chatdb'
    cur = conn.cursor()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur.execute('CREATE DATABASE ' + dbname)
    cur.close()
    conn.close()

    """Connect to created database"""
    conn = psycopg2.connect(dbname=dbname, user='rizwan', host='localhost', password='password123')
    conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)

    """Create a table of usernames"""
    cur = conn.cursor()
    cur.execute('CREATE TABLE usernames(username varchar(30))')
    conn.commit()
    cur.close()
    return conn

@pytest.fixture()
def set_up_server():
    server = chat_server.Server()
    return server


# tests
def test_add_client(set_up_server):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        username = 'test_user'.encode('utf-8')
        s.connect(('127.0.0.1', 1234))
        s.setblocking(False)
        username_header = f'{len(username):<{HEADER_LENGTH}}'.encode('utf-8')
        s.send(username_header + username)
    add_client(set_up_server)
    assert len(set_up_server.clients) == 1


"""This tests the server receiving a message from client socket s1, then broadcasting
it to client socket s2."""
def test_broadcast_message(set_up_server):
    s1 = set_and_send_username('test_user')
    _ = add_client(set_up_server)

    s2 = set_and_send_username('test_user2')
    s2_client_socket = add_client(set_up_server)

    sent_message = 'sent_message'.encode('utf-8')
    sent_message_header = f'{len(sent_message):<{HEADER_LENGTH}}'.encode('utf-8')
    s2.send(sent_message_header + sent_message)

    message = set_up_server.read_message(s2_client_socket)
    set_up_server.broadcast_messages(s2_client_socket, message)

    username_header = s1.recv(HEADER_LENGTH)
    username_length = int(username_header.decode('utf-8').strip())
    __ = s1.recv(username_length).decode('utf-8').strip()
    message_header = s1.recv(HEADER_LENGTH)
    message_length = int(message_header.decode('utf-8').strip())
    message = s1.recv(message_length).decode('utf-8')

    s1.close()
    s2.close()

    assert message == 'sent_message'

def test_duplicate_username_rejected(set_up_server):
    s1 = set_and_send_username('test_user')
    s2 = set_and_send_username('test_user')
    message_header = s2.recv(HEADER_LENGTH)
    message_length = int(message_header.decode('utf-8').strip())
    message = s2.recv(message_length).decode('utf-8')
    assert message == 'Username already taken - please pick another'