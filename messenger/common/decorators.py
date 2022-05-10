import inspect
import logging
import socket
import sys
import traceback


if sys.argv[0].find('client_dist.py') == -1:
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


# class Log:
#     def __call__(self, func):
#         def log_saver(*args, **kwargs):
#             res = func(*args, **kwargs)
#             log.debug(f'Вызов функции: {func.__name__} с параметрами {args}, {kwargs}.'
#                       f'Модуль: {func.__module__}.')
#             return res
#         return log_saver


# class Log:
#     def __call__(self, func):
#         def log_saver(*args, **kwargs):
#             res = func(*args, **kwargs)
#             log.debug(f'Вызов функции: {func.__name__} с параметрами {args}, {kwargs}.'
#                       f'Модуль: {func.__module__}.'
#                       f'Вызов из функции {traceback.format_stack()[0].strip().split()[-1]}.'
#                       f'Вызов из функции {inspect.stack()[1][3]}')
#             return res
#         return log_saver


# def logger(func):
#     def log_saver(*args, **kwargs):
#         log_name = 'server' if 'server.py' in sys.argv[0] else 'client'
#         log = logging.getLogger(log_name)
#
#         res = func(*args, **kwargs)
#         log.debug(f'Функция: {func.__name__}.'
#                   f'Парамаетры: {args}, {kwargs}.'
#                   f'Модуль: {func.__module__}.'
#                   f'Вызов из функции: {traceback.format_stack()[0].strip().split()[-1]}.'
#                   f'Вызов из функции: {inspect.stack()[1][3]}')
#         return res
#     return log_saver
