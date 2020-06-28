import chat_server
import pytest
import socket


@pytest.fixture()
def set_up():
    server = chat_server.Server()
    return server


def test_add_client(set_up):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        username = 'test_user'.encode('utf-8')
        s.connect(('127.0.0.1', 1234))
        s.setblocking(False)
        username_header = f'{len(username):<{16}}'.encode('utf-8')
        s.send(username_header + username)

        client_socket, client_address = set_up.current_socket.accept()
        client_name = set_up.read_message(client_socket)
        set_up.add_client(client_name, client_socket)

    assert len(set_up.clients) == 1


