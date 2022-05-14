import subprocess


def main():
    process = []
    while True:
        ACTION = input(' q - выход\n '
                       's - запустить сервер\n '
                       'c - запустить клиента\n '
                       'x - закрыть все окна\n '
                       'Выберите действие: ')
        if ACTION == 'q':
            break
        elif ACTION == 's':
            process.append(subprocess.Popen('python server_mod.py',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif ACTION == 'c':
            print('Первый запуск может быть достаточно долгим из-за генерации ключей!')
            clients_count = int(input('Введите количество клиентов для запуска: '))

            for i in range(clients_count):
                process.append(subprocess.Popen(f'python client.py -n test{i+1} -p 123456 ',
                                                creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif ACTION == 'x':
            while process:
                process.pop().kill()


if __name__ == '__main__':
    main()
