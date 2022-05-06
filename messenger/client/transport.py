import json
import logging
import socket
import sys
import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal

from common.utils import send_message, get_message
from common.variables import *
from common.errors import *

sys.path.append('../')

log = logging.getLogger('client_dist')
socket_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):
    new_message = pyqtSignal(str)
    connect_lost = pyqtSignal()

    def __init__(self, port, ip_address, database, username):
        threading.Thread.__init__(self)
        QObject.__init__(self)
        self.database = database
        self.username = username
        self.transport = None
        self.connect_init(port, ip_address)

        try:
            self.user_list_request()
            self.contacts_list_request()
        except OSError as err:
            if err.errno:
                raise ServerError('Потеряно соединение с сервером.')
        except json.JSONDecodeError:
            raise ServerError('Потеряно соединение с сервером.')
        self.running = True

    def connect_init(self, port, ip):
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)
        connected = False
        for i in range(5):
            log.info(f'Попытка подключения №{i + 1}')
            try:
                self.transport.connect((ip, port))
            except (OSError, ConnectionRefusedError) as e:
                print(e)
                # pass
            else:
                connected = True
                break
            time.sleep(1)

        if not connected:
            raise ServerError('Не удалось установить соединение с сервером.')

        log.debug('Установлено соединение с сервером')

        try:
            with socket_lock:
                send_message(self.transport, self.create_presence())
                self.process_response_ans(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            raise ServerError('Потеряно соединение с сервером.')

        log.info('Соединение успешно установлено')

    def create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username
            }
        }
        log.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.username}')
        return out

    def process_response_ans(self, message):
        log.debug(f'Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
            else:
                print(f'Неизвестный код {message[RESPONSE]}')

        elif ACTION in message and message[ACTION] == MESSAGE \
                and SENDER in message \
                and DESTINATION in message \
                and MESSAGE_TEXT in message \
                and message[DESTINATION] == self.username:
            log.debug(f'\n Получено сообщение от пользователя '
                      f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
            self.database.save_message(message[SENDER], 'in', message[MESSAGE_TEXT])
            self.new_message.emit(message[SENDER])

    def contacts_list_request(self):
        log.debug(f'Запрос контакт листа для пользователя {self.name}')
        req = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        log.debug(f'Сформирован запрос {req}')
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        log.debug(f'Получен ответ {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            for contact in ans[LIST_INFO]:
                self.database.add_contact(contact)
        else:
            log.error('Не удалось обновить список контактов')
            raise ServerError

    def user_list_request(self):
        log.debug(f'Запрос списка известных пользователей {self.username}')
        req = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            self.database.add_users(ans[LIST_INFO])
        else:
            log.error('Не удалось обновить список контактов')
            raise ServerError

    def add_contact(self, contact):
        log.debug(f'Создание контакта {contact}')
        req = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }

        with socket_lock:
            send_message(self.transport, req)
            self.process_response_ans(get_message(self.transport))

    def remove_contact(self, contact):
        log.debug(f'Удаление контакта {contact}')
        req = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, req)
            self.process_response_ans(get_message(self.transport))

    def transport_error(self):
        self.running = False
        message = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            try:
                send_message(self.transport, message)
            except OSError as err:
                log.debug(f'{err}')
        log.debug('Ошибка в работе транспорта')
        time.sleep(0.5)

    def send_message(self, to, message):
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        log.debug(f'Сформирован словарь сообщения: {message_dict}')

        with socket_lock:
            try:
                send_message(self.transport, message_dict)
                self.process_response_ans(get_message(self.transport))
                log.info(f'Отправлено сообщение для пользователя {to}')
            except OSError as err:
                if err.errno:
                    log.critical('Потеряно соединение с сервером.')
                    exit(1)
                else:
                    log.error('Не удалось передать сообщение. Таймаут соединения')

    def run(self):
        log.debug('Запущен процесс')
        while self.running:
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        log.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connect_lost.emit()
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    log.critical(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connect_lost.emit()
                else:
                    log.debug(f'Принято сообщение с сервера: {message}')
                    self.process_response_ans(message)
                finally:
                    self.transport.settimeout(5)





