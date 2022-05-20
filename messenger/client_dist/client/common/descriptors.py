import logging
import sys


if sys.argv[0].find('client_dist') == -1:
    log = logging.getLogger('server_dist')
else:
    log = logging.getLogger('client_dist')


class Port:
    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            log.critical(f'Некорректный порт {value}')
            # exit(1)
            raise TypeError('Некорректный номер порта')
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
