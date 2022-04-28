import platform
import threading
from subprocess import Popen, PIPE
from ipaddress import ip_address
from tabulate import tabulate

result = {'reachable': '', 'unreachable': ''}


def host_ping(hosts_list, res=False):
    for host in hosts_list:
        try:
            ipv4 = ip_address(host)
        except Exception as e:
            print(e)
            ipv4 = host

        param = '-n' if platform.system().lower() == 'windows' else '-c'
        response = Popen(['ping', param, '1', '-w', '1', str(ipv4)], stdout=PIPE)

        if response.wait() == 0:
            result['reachable'] += f'{ipv4}\n'
            res_str = f'{ipv4} - Узел доступен'
        else:
            result['unreachable'] += f'{ipv4}\n'
            res_str = f'{ipv4} - Узел недоступен'
        print(res_str)
    return result


def host_range_ping(res=False):
    while True:
        IP = input('Введите адрес: ')
        try:
            start = ip_address(IP)
            octet = int(IP.split('.')[3])
            break
        except Exception as e:
            print(e)
    while True:
        num = input('Введите количество проверяемых адресов: ')
        if not num.isnumeric():
            print('Должно быть число')
        else:
            if (octet + int(num)) > 255 + 1:
                print(f'Максимальное число хостов {255 + 1 - octet}')
            else:
                break

    host_list = []
    [host_list.append(str(start + x)) for x in range(int(num))]

    thread = threading.Thread(target=host_ping, args=(hosts_list, ), daemon=True)
    thread.start()
    host_list.append(thread)

    if not res:
        host_ping(host_list)
    else:
        return host_ping(host_list)


def host_range_ping_tab():
    out = host_range_ping(True)
    print()
    print(tabulate([out], headers='keys', tablefmt='pipe', stralign='center'))


if __name__ == '__main__':
    hosts = ['192.125.1.10', '8.8.8.8', 'yandex.ru', 'google.com',
                  '0.0.0.1', '0.0.0.2', '0.0.0.3', '0.0.0.4', '0.0.0.5']
    host_ping(hosts)
    host_range_ping()
    host_range_ping_tab()
