import argparse
import logging
import os
import threading
import sys

from Cryptodome.PublicKey import RSA
from PyQt5.QtWidgets import QApplication, QMessageBox

from client_mod.main_window import ClientMainWindow
from client_mod.start_dialog import UserNameDialog
from client_mod.transport import ClientTransport
from common.decorators import logger
from common.variables import *
from common.utils import *
from common.errors import ServerError
from client_mod.client_db import ClientDatabase
import logs.client_log_config

log = logging.getLogger('client_dist')


@logger
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password

    if not 1023 < server_port < 65536:
        log.critical('Порт должен быть указан в пределах от 1024 до 65535')
        exit(1)

    return server_address, server_port, client_name, client_passwd


if __name__ == '__main__':

    server_address, server_port, client_name, client_passwd = arg_parser()

    client_app = QApplication(sys.argv)
    start_dialog = UserNameDialog()

    if not client_name or not client_passwd:
        client_app.exec_()
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_passwd = start_dialog.client_passwd.text()
        else:
            exit(0)

    log.info(f'Запущен пользователь: {client_name}, порт: {server_port}')

    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_name}.key')

    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    database = ClientDatabase(client_name)

    try:
        transport = ClientTransport(server_port, server_address,
                                    database, client_name, client_passwd,
                                    keys)
    except ServerError as err:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера', err.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()
    del start_dialog

    main_window = ClientMainWindow(database, transport, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Мессенджер - {client_name}')
    client_app.exec_()

    transport.transport_error()
    transport.join()

