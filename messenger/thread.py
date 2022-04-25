from ipaddress import ip_address
from subprocess import Popen, PIPE

from tabulate import tabulate

result = {'reachable': '', 'unreachable': ''}


def host_ping(hosts_list, time_out=500, request=1):
    for host in hosts_list:
        try:
            ipv4 = ip_address(host)
        except ValueError as val:
            print(f'{val}')
            continue
        response = Popen(['ping', f'{host}', '-w', f'{time_out}', '-n', f'{request}'], shell=False, stdout=PIPE)
        response.wait()
        if response.returncode == 0:
            result['reachable'] += f'{str(host)}\n'
            res_str = f'{ipv4} - Узел доступен'
        else:
            result['unreachable'] += f'{str(host)}\n'
            res_str = f'{ipv4} - Узел недоступен'
        print(res_str)
    return result


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

    hosts_list = []
    [hosts_list.append(str(ip_address(IP) + x)) for x in range(int(num))]
    return host_ping(hosts_list)


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
