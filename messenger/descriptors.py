import logging

server_log = logging.getLogger('server_dist')


class Port:
    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            server_log.critical(f'Неподходящий порт {value}')
            exit(1)
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
