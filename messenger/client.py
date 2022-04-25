import argparse
import sys
import json
import socket
import threading
import time
import logging
import logs.client_log_config
from common.decorators import Log
from common.variables import *
from common.utils import get_message, send_message
from errors import ServerError, ReqFieldMissingError, IncorrectDataRecivedError
from metaclasses import ClientVerifier

client_log = logging.getLogger('client')


class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        super().__init__()
        self.account_name = account_name
        self.sock = sock

    def print_help(self):
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name,
        }

    def create_message(self):
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message,
        }
        client_log.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            client_log.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            client_log.critical('Потеряно соединение с сервером.')
            exit(1)

    def run(self):
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message' or command == 'm':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                try:
                    send_message(self.sock, self.create_exit_message())
                except:
                    pass
                print('Завершение соединения.')
                client_log.info('Завершение работы по команде пользователя.')
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробуйте снова. help - вывести поддерживаемые команды.')


class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        super().__init__()
        self.account_name = account_name
        self.sock = sock

    def run(self):
        while True:
            try:
                message = get_message(self.sock)
                if ACTION in message and message[ACTION] == MESSAGE and \
                        SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                    print(f'Получено сообщение от пользователя '
                          f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    client_log.info(f'Получено сообщение от пользователя '
                                    f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                else:
                    client_log.error(f'Получено некорректное сообщение от сервера: {message}')
            except IncorrectDataRecivedError:
                client_log.error('Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                client_log.critical('Потеряно соединение с сервером.')
                break


@Log()
def create_presence(account_name='Guest'):
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    client_log.debug(f'Создание {PRESENCE} сообщения для пользователя {account_name}.')
    return out


@Log()
def process_response_ans(message):
    client_log.info(f'Обработка сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            client_log.info('Успешная обработка сообшения от сервера.')
            return '200 : OK'
        client_log.critical('Не успешная обработка сообщения от сервера.')
        return f'400 : {message[ERROR]}'
    raise ValueError


@Log()
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default='listen', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if not 1023 < server_port < 65536:
        client_log.critical('Порт должен быть указан в пределах от 1024 до 65535')
        exit(1)

    return server_address, server_port, client_name


def main():
    server_address, server_port, client_name = arg_parser()

    print(f'Консольный месседжер. Клиентский модуль. Имя пользователя: {client_name}')

    if not client_name:
        client_name = input('Введите имя пользователя: ')
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    client_log.info(f'Запущен клиент с параметрами: адрес сервера: {server_address}, '
                    f'порт: {server_port}, режим работы: {client_name}')
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_response_ans(get_message(transport))
        client_log.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print('Установлено соединение с сервером.')
    except json.JSONDecodeError:
        client_log.error('Не удалось декодировать полученную Json строку.')
        exit(1)
    except ServerError as err:
        client_log.error(f'При установке соединения сервер вернул ошибку: {err.text}')
        exit(1)
    except ReqFieldMissingError as missing_err:
        client_log.error(f'В ответе сервера отсутствует необходимое поле: {missing_err.missing_field}')
        exit(1)
    except (ConnectionRefusedError, ConnectionError):
        client_log.critical(
            f'Не удалось подключится к серверу {server_address}:{server_port}, '
            f'Конечный компьютер отверг запрос на подключение')
        exit(1)
    else:
        module_receiver = ClientReader(client_name, transport)
        module_receiver.daemon = True
        module_receiver.start()

        module_sender = ClientSender(client_name, transport)
        module_sender.daemon = True
        module_sender.start()
        client_log.debug('Запущены процессы')

        while True:
            time.sleep(1)
            if module_receiver.is_alive() and module_sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
