import shlex

from primitive_db.core import create_table, drop_table, list_tables
from primitive_db.utils import load_metadata, save_metadata

METADATA_FILE = "db_meta.json"


def print_help():
    """Prints the help message for the current mode."""

    print("\n***Процесс работы с таблицей***")
    print("Функции:")
    print(
        "<command> create_table <имя_таблицы> "
        "<столбец1:тип> .. - создать таблицу"
    )
    print("<command> list_tables - показать список всех таблиц")
    print("<command> drop_table <имя_таблицы> - удалить таблицу")

    print("\nОбщие команды:")
    print("<command> exit - выход из программы")
    print("<command> help - справочная информация\n")


def run():
    while True:
        metadata = load_metadata(METADATA_FILE)

        print("\n***Процесс работы с таблицей***")
        print_help()

        user_input = input(">>>Введите команду: ")

        try:
            args = shlex.split(user_input)
        except ValueError:
            print("Некорректное значение. Попробуйте снова.")
            continue

        if not args:
            continue

        command = args[0]

        if command == "create_table":
            if len(args) < 3:
                print("Некорректное значение. Попробуйте снова.")
                continue

            table_name = args[1]
            columns = args[2:]

            old_metadata = metadata.copy()
            metadata = create_table(metadata, table_name, columns)

            if metadata != old_metadata:
                save_metadata(METADATA_FILE, metadata)

        elif command == "drop_table":
            if len(args) != 2:
                print("Некорректное значение. Попробуйте снова.")
                continue

            table_name = args[1]

            old_metadata = metadata.copy()
            metadata = drop_table(metadata, table_name)

            if metadata != old_metadata:
                save_metadata(METADATA_FILE, metadata)

        elif command == "list_tables":
            if len(args) != 1:
                print("Некорректное значение. Попробуйте снова.")
                continue

            list_tables(metadata)

        elif command == "help":
            if len(args) != 1:
                print("Некорректное значение. Попробуйте снова.")
                continue

            print_help()

        elif command == "exit":
            if len(args) != 1:
                print("Некорректное значение. Попробуйте снова.")
                continue

            break

        else:
            print(f"Функции {command} нет. Попробуйте снова.")