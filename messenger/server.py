import socket
import sys
import logging
import argparse
import select
import time
import logs.server_log_config

from common.decorators import Log
from common.variables import *
from common.utils import get_message, send_message
from descriptors import Port
from metaclasses import ServerVerifier

server_log = logging.getLogger('server')


@Log()
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server(metaclass=ServerVerifier):
    port = Port()

    def __init__(self, listen_address, listen_port):
        self.addr = listen_address
        self.port = listen_port

        self.clients = []
        self.messages = []
        self.names = dict()

    def init_socket(self):

        server_log.info(f'Сервер запущен на порту: {self.addr}, '
                        f'по адресу: {self.port}')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen()

    def main_loop(self):

        self.init_socket()

        while True:
            try:
                client, client_address = self.sock.accept()
            except OSError as err:
                # print(err)
                pass
            else:
                server_log.info(f'Установлено соединение с ПК {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []

            try:
                if self.clients:
                    recv_data_lst, send_data_lst, _ = select.select(self.clients, self.clients, [], 0)
            except OSError as err:
                print(err)

            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(get_message(client_with_message),
                                                    client_with_message)
                    except:
                        server_log.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        self.clients.remove(client_with_message)

            for message in self.messages:
                try:
                    self.process_message(message, send_data_lst)
                except Exception as err:
                    print(err)
                    server_log.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            server_log.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                            f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            server_log.error(f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                             'отправка сообщения невозможна.')

    def process_client_message(self, message, client):

        server_log.debug(f'Обработка сообщения от клиента: {message}')

        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message:

            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                send_message(client, {RESPONSE: 200})
            else:
                response = RESPONDEFAULT_IP_ADDRESS
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            return
        else:
            response = RESPONDEFAULT_IP_ADDRESS
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def main():
    listen_address, listen_port = arg_parser()

    server = Server(listen_address, listen_port)
    server.main_loop()


if __name__ == '__main__':
    main()
