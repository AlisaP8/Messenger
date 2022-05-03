import subprocess

process_list = []

while True:
    ACTION = input('Выберите действие: q - выход, '
                   's - запустить сервер и клиенты, '
                   'x - закрыть все окна: ')

    if ACTION == 'q':
        break
    elif ACTION == 's':
        clients_count = int(input('Введите количество клиентов для запуска: '))
        process_list.append(subprocess.Popen('python server.py',
                                             creationflags=subprocess.CREATE_NEW_CONSOLE))
        for i in range(clients_count):
            process_list.append(subprocess.Popen(f'python client.py -n test{i+1}',
                                                 creationflags=subprocess.CREATE_NEW_CONSOLE))

    elif ACTION == 'x':
        while process_list:
            process_list.pop().kill()

    # elif ACTION == 'x':
    #     for process in process_list:
    #         process.kill()
    #     process_list.clear()
    # else:
    #     print('Ошибка')
