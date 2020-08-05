import chat_server
import pytest
import socket
import psycopg2
import select
import psycopg2.errors


HEADER_LENGTH = 16


def add_client(server):
    client_socket, client_address = server.server_socket.accept()
    client_name = server.read_message(client_socket)
    server.add_client(client_name, client_socket, client_address)
    return client_socket

def set_and_send_username(username):
    username = username.encode('utf-8')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 1234))
    username_header = f'{len(username):<{HEADER_LENGTH}}'.encode('utf-8')
    s.send(username_header + username)
    return s


@pytest.fixture()
def set_up_server():
    server = chat_server.Server('127.0.0.1', 1234)
    return server


"""Tests"""
def test_add_client(set_up_server):
    print('test add client started....')
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
    print('print runs in test')
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


"""This tests the server rejecting a duplicate username,"""
def test_duplicate_username_rejected(set_up_server):
    db_connection = set_up_server.create_username_database()
    s1 = set_and_send_username('test_user')
    client_socket, client_address = set_up_server.server_socket.accept()
    _ = chat_server.accept_username(db_connection, client_socket, set_up_server)
    set_up_server.sockets_list.append(client_socket)

    s2 = set_and_send_username('test_user')
    read_sockets, _, exception_sockets = select.select(set_up_server.sockets_list, [], set_up_server.sockets_list)
    for socket in read_sockets:
        if socket == set_up_server.server_socket:
            client_socket, client_address = set_up_server.server_socket.accept()
            _ = chat_server.accept_username(db_connection, client_socket, set_up_server)
    message_header = s2.recv(HEADER_LENGTH)
    message_length = int(message_header.decode('utf-8').strip())
    message = s2.recv(message_length).decode('utf-8')
    assert message == 'Username already taken - please enter another'