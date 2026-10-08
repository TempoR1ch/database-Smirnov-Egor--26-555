import prompt


def welcome():
    while True:
        print("<command> exit - выйти из программы")
        print("<command> help - справочная информация")

        command = prompt.string("Введите команду: ")

        if command == "exit":
            break

        if command == "help":
            continue