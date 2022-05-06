import argparse
import logging
import threading
import sys
from PyQt5.QtWidgets import QApplication

from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog
from client.transport import ClientTransport
from common.variables import *
from common.utils import *
from common.errors import ServerError
from client.client_db import ClientDatabase
# import logs.client_log_config


log = logging.getLogger('client_dist')


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if not 1023 < server_port < 65536:
        log.critical('Порт должен быть указан в пределах от 1024 до 65535')
        exit(1)

    return server_address, server_port, client_name


if __name__ == '__main__':

    server_address, server_port, client_name = arg_parser()

    client_app = QApplication(sys.argv)

    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    log.info(f'Запущен пользователь: {client_name}, порт: {server_port}')

    database = ClientDatabase(client_name)
    try:
        transport = ClientTransport(server_port, server_address, database, client_name)
    except ServerError as err:
        print(err)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    main_window = ClientMainWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Мессенджер - {client_name}')
    client_app.exec_()

    transport.transport_error()
    transport.join()

