from ipaddress import ip_address
from subprocess import Popen, PIPE

from tabulate import tabulate

res = {'reachable': '', 'unreachable': ''}


def host_ping(list_ping, time_out=500, request=1):
    for ip_addr in list_ping:
        try:
            addr = ip_address(ip_addr)
            print(addr)
        except ValueError as val:
            print(f'{val}')
            continue
        ping_proc = Popen(f'ping {ip_addr} -w {time_out} -n {request}', shell=False, stdout=PIPE)
        ping_proc.wait()
        if ping_proc.returncode == 0:
            res['reachable'] += f'{str(ip_addr)}\n'
        else:
            res['unreachable'] += f'{str(ip_addr)}\n'
    return res


def host_range_ping():
    while True:
        IP = input('Введите адрес: ')
        try:
            octet = int(IP.split('.')[3])
            break
        except Exception as e:
            print(e)

    while True:
        num = input('Введите количество проверяемых адресов: ')
        if not num.isnumeric():
            print('Должно быть число')
        else:
            if (octet + int(num)) > 255:
                print(f'Вы превысили максиум {255 - octet}')
            else:
                break

    hosts = []
    [hosts.append(str(ip_address(IP) + x)) for x in range(int(num))]
    return host_ping(hosts)


def host_range_ping_tab():
    out = host_range_ping()
    print()
    print(tabulate([out], headers='keys', tablefmt='pipe', stralign='center'))


if __name__ == '__main__':
    hosts = ['google.com', 'yandex.ru', '192.152.1.10', '8.8.8.8', '0.0.0.1',
             '0.0.0.2', '0.0.0.3', '0.0.0.4', '0.0.0.5']
    host_ping(hosts)
    host_range_ping()
    host_range_ping_tab()
