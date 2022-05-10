import binascii
import hashlib
import hmac
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

    new_message = pyqtSignal(dict)
    connect_lost = pyqtSignal()
    message_205 = pyqtSignal()

    def __init__(self, port, ip_address, database, username, passwd, keys):
        threading.Thread.__init__(self)
        QObject.__init__(self)
        self.database = database
        self.username = username
        self.passwd = passwd
        self.keys = keys
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
                log.debug('Соединение установлено')
                break
            time.sleep(1)

        if not connected:
            raise ServerError('Не удалось установить соединение с сервером.')

        log.debug('Установлено соединение с сервером')

        passwd_bytes = self.passwd.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        passwd_hash = hashlib.pbkdf2_hmac('sha512', passwd_bytes, salt, 10000)
        passwd_hash_str = binascii.hexlify(passwd_hash)
        log.debug(f'Хэш пароля: {passwd_hash_str}')

        pubkey = self.keys.publickey().export_key().decode('ascii')

        with socket_lock:
            presense = {
                ACTION: PRESENCE,
                TIME: time.time(),
                USER: {
                    ACCOUNT_NAME: self.username,
                    PUBLIC_KEY: pubkey,
                }
            }
            try:
                send_message(self.transport, presense)
                ans = get_message(self.transport)
                log.debug(f'Ответ сервера = {ans}.')

                if RESPONSE in ans:
                    if ans[RESPONSE] == 400:
                        raise ServerError(ans[ERROR])
                    elif ans[RESPONSE] == 511:
                        ans_data = ans[DATA]
                        hash = hmac.new(passwd_hash_str, ans_data.encode('utf-8'), 'MD5')
                        digest = hash.digest()
                        my_ans = RESPONSE_511
                        my_ans[DATA] = binascii.b2a_base64(digest).decode('ascii')
                        send_message(self.transport, my_ans)
                        self.process_response_ans(get_message(self.transport))
            except (OSError, json.JSONDecodeError) as err:
                log.debug('Ошибка соединения', exc_info=err)
                raise ServerError('Сбой соединения в процессе авторизации.')

        log.info('Соединение успешно установлено')

    # def create_presence(self):
    #     out = {
    #         ACTION: PRESENCE,
    #         TIME: time.time(),
    #         USER: {
    #             ACCOUNT_NAME: self.username
    #         }
    #     }
    #     log.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.username}')
    #     return out

    def process_response_ans(self, message):
        log.debug(f'Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.user_list_request()
                self.contacts_list_request()
                self.message_205.emit()
            else:
                print(f'Неизвестный код {message[RESPONSE]}')

        elif ACTION in message and message[ACTION] == MESSAGE \
                and SENDER in message \
                and DESTINATION in message \
                and MESSAGE_TEXT in message \
                and message[DESTINATION] == self.username:
            log.debug(f'\n Получено сообщение от пользователя '
                      f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
            self.new_message.emit(message)

    def contacts_list_request(self):
        self.database.contacts_clear()
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

    def key_request(self, user):
        log.debug(f'Запрос публичного ключа для {user}')
        req = {
            ACTION: PUBLIC_KEY_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: user
        }
        with socket_lock:
            send_message(self.transport, req)
            ans = get_message(self.transport)
        if RESPONSE in ans and ans[RESPONSE] == 511:
            return ans[DATA]
        else:
            log.error(f'Не удалось получить ключ собеседника{user}.')

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
            send_message(self.transport, message_dict)
            self.process_response_ans(get_message(self.transport))
            log.info(f'Отправлено сообщение для пользователя {to}')

    def run(self):
        log.debug('Запущен процесс')
        while self.running:
            time.sleep(1)
            message = None
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
                finally:
                    self.transport.settimeout(5)

            if message:
                log.debug(f'Принято сообщение с сервера: {message}')
                self.process_response_ans(message)





