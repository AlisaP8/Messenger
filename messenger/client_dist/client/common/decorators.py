import logging
import socket
import sys
sys.path.append('../')

if sys.argv[0].find('client_dist') == -1:
    log = logging.getLogger('server_dist')
else:
    log = logging.getLogger('client_dist')


def logger(func):

    def log_saver(*args, **kwargs):
        log.debug(f'Вызов функции: {func.__name__} с параметрами {args}, {kwargs}.'
                  f'Модуль: {func.__module__}.')
        res = func(*args, **kwargs)
        return res

    return log_saver


def login_required(func):

    def checker(*args, **kwargs):
        from server.base import MessageProcess
        from common.variables import ACTION, PRESENCE

        if isinstance(args[0], MessageProcess):
            found = False
            for arg in args:
                if isinstance(arg, socket.socket):
                    for client in args[0].names:
                        if args[0].names[client] == arg:
                            found = True

            for arg in args:
                if isinstance(arg, dict):
                    if ACTION in arg and arg[ACTION] == PRESENCE:
                        found = True

            if not found:
                raise TypeError
        return func(*args, **kwargs)

    return checker


