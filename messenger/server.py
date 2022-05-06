import configparser
import os
import socket
import sys
import logging
import argparse
import select
import threading
import time

from PyQt5.QtCore import QTimer

# import logs.log_config_server
from PyQt5.QtWidgets import QApplication, QMessageBox
# from common.decorators import Log
from common.variables import *
from common.utils import get_message, send_message
from server_db import ServerStorage
from descriptors import Port
from metaclasses import ServerVerifier
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow

log = logging.getLogger('server_dist')
new_connect = False
flag_lock = threading.Lock()


# @Log()
def arg_parser(default_port, default_address):
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

        log.info(f'Сервер запущен на порту: {self.addr}, '
                 f'по адресу: {self.port}')
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen()

    def run(self):
        global new_connect
        self.init_socket()

        while True:
            try:
                client, client_address = self.sock.accept()
            except OSError as err:
                # print(err)
                pass
            else:
                log.info(f'Установлено соединение с ПК {client_address}')
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
                    except OSError:
                        log.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')

                        for name in self.names:
                            if self.names[name] == client_with_message:
                                self.database.user_logout(name)
                                del self.names[name]
                                break
                        self.clients.remove(client_with_message)
                        with flag_lock:
                            new_connect = True

            for message in self.messages:
                try:
                    self.process_message(message, send_data_lst)
                except Exception as err:
                    print(err)
                    log.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    self.database.user_logout(message[DESTINATION])
                    del self.names[message[DESTINATION]]
                    with flag_lock:
                        new_connect = True
            self.messages.clear()

    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names \
                and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            log.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                     f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names \
                and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            log.error(f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                      'отправка сообщения невозможна.')

    def process_client_message(self, message, client):
        global new_connect

        log.debug(f'Обработка сообщения от клиента: {message}')

        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message \
                and USER in message:

            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME],
                                         client_ip, client_port)
                send_message(client, {RESPONSE: 200})
                with flag_lock:
                    new_connect = True
            else:
                response = RESPONDEFAULT_IP_ADDRESS
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return

        elif ACTION in message and message[ACTION] == MESSAGE \
                and DESTINATION in message \
                and TIME in message \
                and SENDER in message \
                and MESSAGE_TEXT in message \
                and self.names[message[SENDER]] == client:
            if message[DESTINATION] in self.names:
                self.messages.append(message)
                self.database.process_message(message[SENDER],
                                          message[DESTINATION])
                send_message(client, {RESPONSE: 200})
            else:
                response = RESPONDEFAULT_IP_ADDRESS
                response[ERROR] = 'Пользователь не зарегистрирован'
            return

        elif ACTION in message and message[ACTION] == EXIT \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with flag_lock:
                new_connect = True
            return

        elif ACTION in message and message[ACTION] == GET_CONTACTS \
                and USER in message \
                and self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            send_message(client, response)

        elif ACTION in message and message[ACTION] == ADD_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, {RESPONSE: 200})

        elif ACTION in message and message[ACTION] == REMOVE_CONTACT \
                and ACCOUNT_NAME in message \
                and USER in message \
                and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, {RESPONSE: 200})

        elif ACTION in message and message[ACTION] == USERS_REQUEST \
                and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.users_list()]
            send_message(client, response)

        else:
            response = RESPONDEFAULT_IP_ADDRESS
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def config_load():
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_database.db3')
        return config


def main():

    config = config_load()

    listen_address, listen_port = arg_parser(config['SETTINGS']['Default_port'],
                                             config['SETTINGS']['Listen_Address'])

    database = ServerStorage(
        os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file']))

    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    main_window.statusBar().showMessage('Connected Server')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    def list_update():
        global new_connect
        if new_connect:
            main_window.active_clients_table.setModel(gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with flag_lock:
                new_connect = False

    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    def server_config():
        global config_window
        config_window =ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['Database_path'])
        config_window.db_file.insert(config['SETTINGS']['Database_file'])
        config_window.port.insert(config['SETTINGS']['Default_port'])
        config_window.ip.insert(config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(save_server_config)

    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['Database_path'] = config_window.db_path.text()
        config['SETTINGS']['Database_file'] = config_window.db_file.text()

        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка, не число')
        else:
            config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['Default_port'] = str(port)
                dir_path = os.path.dirname(os.path.realpath(__file__))
                print(port)
                with open(f"{dir_path}/{'server_dist.ini'}", 'w') as conf:
                    config.write(conf)
                    message.information(config_window,
                                        'ОК', 'Настройки успешно сохранены!')
            else:
                message.warning(config_window, 'Ошибка', 'Неверный диапазон')

    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    server_app.exec_()


if __name__ == '__main__':
    main()

