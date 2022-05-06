import subprocess

process_list = []

while True:
    ACTION = input(' q - выход\n '
                   's - запустить сервер\n '
                   'c - запустить клиента\n '
                   'x - закрыть все окна\n '
                   'Выберите действие: ')

    if ACTION == 'q':
        break
    elif ACTION == 's':
        process_list.append(subprocess.Popen('python server.py',
                                             creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif ACTION == 'c':
        clients_count = int(input('Введите количество клиентов для запуска: '))

        for i in range(clients_count):
            process_list.append(subprocess.Popen(f'python client.py -n test{i+1}',
                                                 creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif ACTION == 'x':
        while process_list:
            process_list.pop().kill()
