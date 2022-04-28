import socket
import sys
import logging
import argparse
import select
import threading
import time
import logs.server_log_config

from common.decorators import Log
from common.variables import *
from common.utils import get_message, send_message
from database_server import ServerStorage
from descriptors import Port
from metaclasses import ServerVerifier

server_log = logging.getLogger('server_dist')


@Log()
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server(threading.Thread, metaclass=ServerVerifier):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        super().__init__()
        self.addr = listen_address
        self.port = listen_port

        self.database = database
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

    def run(self):

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
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
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
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            return
        else:
            response = RESPONDEFAULT_IP_ADDRESS
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def print_help():
    print('Поддерживаемые команды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    listen_address, listen_port = arg_parser()

    database = ServerStorage()

    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    print_help()

    while True:
        command = input('Введите команду: ')
        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input('Введите имя пользователя для просмотра истории. '
                         'Нажмите Enter для вывода всей истории: ')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    main()
