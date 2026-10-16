import shlex

from prettytable import PrettyTable

from primitive_db.constants import METADATA_FILE
from primitive_db.core import (
    clear_select_cache,
    create_table,
    delete,
    drop_table,
    insert,
    list_tables,
    select,
    update,
)
from primitive_db.parser import (
    parse_condition,
    parse_set_clause,
    parse_values,
    split_keyword,
    validate_clause,
)
from primitive_db.utils import (
    delete_table_file,
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)


def print_help():
    """Выводит список доступных команд."""
    print(
        """
***Операции с данными***
Функции:
create_table <имя_таблицы> <столбец:тип> ... - создать таблицу
drop_table <имя_таблицы> - удалить таблицу
list_tables - вывести список таблиц
insert into <имя_таблицы> values (<значение1>, ...) - добавить запись
select from <имя_таблицы> where <столбец> = <значение> - прочитать записи
update <имя_таблицы> set <столбец>=<значение> where <условие> - обновить записи
delete from <имя_таблицы> where <условие> - удалить записи
info <имя_таблицы> - информация о таблице
help - вывести справку
exit - завершить работу
"""
    )


def print_records(metadata, table_name, records):
    """Выводит записи таблицы в виде таблицы."""
    if table_name not in metadata:
        print(f'Таблица "{table_name}" не существует.')
        return

    if not records:
        print("Записи не найдены.")
        return

    table = PrettyTable()
    columns = [column.split(":", 1)[0] for column in metadata[table_name]["columns"]]
    table.field_names = columns

    for record in records:
        table.add_row([record.get(column) for column in columns])

    print(table)


def run():
    """Запускает интерактивную оболочку базы данных."""
    metadata = load_metadata(METADATA_FILE)

    while True:
        try:
            command_line = input("Введите команду: ").strip()

            if not command_line:
                continue

            args = shlex.split(command_line, posix=False)
            command = args[0].lower()

            if command == "help":
                print_help()

            elif command == "exit":
                print("Работа завершена.")
                break

            elif command == "list_tables":
                list_tables(metadata)

            elif command == "create_table":
                if len(args) < 3:
                    print("Укажите имя таблицы и хотя бы один столбец.")
                    continue

                table_name = args[1]
                columns = args[2:]
                new_metadata = create_table(metadata, table_name, columns)

                if new_metadata is not None:
                    metadata = new_metadata
                    save_metadata(METADATA_FILE, metadata)

            elif command == "drop_table":
                if len(args) != 2:
                    print("Укажите имя таблицы.")
                    continue

                table_name = args[1]

                if table_name not in metadata:
                    print(f'Ошибка: Таблица "{table_name}" не существует.')
                    continue

                old_metadata = metadata.copy()
                new_metadata = drop_table(metadata, table_name)

                if new_metadata is None:
                    continue

                metadata = new_metadata

                if metadata != old_metadata:
                    save_metadata(METADATA_FILE, metadata)
                    delete_table_file(table_name)
                    clear_select_cache()

            elif command == "insert":
                if len(args) < 5 or args[1].lower() != "into":
                    print("Использование: insert into <таблица> values (...)")
                    continue

                table_name = args[2]

                if args[3].lower() != "values":
                    print("Ожидается ключевое слово values.")
                    continue

                values_text = " ".join(args[4:]).strip()

                valid_values = values_text.startswith("(") and values_text.endswith(")")
                quote = None
                depth = 0

                for index, char in enumerate(values_text):
                    if char in ("'", '"'):
                        if quote is None:
                            quote = char
                        elif quote == char:
                            quote = None
                    elif quote is None:
                        if char == "(":
                            depth += 1
                        elif char == ")":
                            depth -= 1
                            if depth < 0 or (
                                depth == 0 and index != len(values_text) - 1
                            ):
                                valid_values = False
                                break

                if not valid_values or quote is not None or depth != 0:
                    print("Ошибка: значения должны быть заключены в скобки.")
                    continue

                values = parse_values(values_text[1:-1])
                table_data = load_table_data(table_name)
                new_data = insert(metadata, table_name, values, table_data)

                if new_data is not None and new_data != table_data:
                    save_table_data(table_name, new_data)
                    clear_select_cache()

            elif command == "select":
                if len(args) < 3 or args[1].lower() != "from":
                    print("Использование: select from <таблица> where <условие>")
                    continue

                table_name = args[2]

                if table_name not in metadata:
                    print(f'Ошибка: Таблица "{table_name}" не существует.')
                    continue

                where_clause = None
                where_parts = split_keyword(" ".join(args[3:]), "where")

                if where_parts is not None:
                    where_clause = parse_condition(where_parts[1])
                    validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                records = select(table_data, where_clause, table_name)

                if records is not None:
                    print_records(metadata, table_name, records)

            elif command == "update":
                if len(args) < 2:
                    print("Укажите имя таблицы.")
                    continue

                table_name = args[1]
                parts = split_keyword(" ".join(args[2:]), "set")

                if parts is None:
                    print("Не найдено ключевое слово set.")
                    continue

                rest = parts[1]
                set_parts = split_keyword(rest, "where")

                if set_parts is None:
                    print("Не найдено ключевое слово where.")
                    continue

                set_clause = parse_set_clause(set_parts[0])
                where_clause = parse_condition(set_parts[1])

                validate_clause(metadata, table_name, set_clause, allow_id=False)
                validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                matching = select(table_data, where_clause, table_name)

                if not matching:
                    print("Записи не найдены.")
                    continue

                new_data = update(
                    table_data, set_clause, where_clause, metadata, table_name
                )

                if new_data is not None:
                    save_table_data(table_name, new_data)
                    clear_select_cache()
                    print("Записи успешно обновлены.")

            elif command == "delete":
                if len(args) < 4 or args[1].lower() != "from":
                    print("Использование: delete from <таблица> where <условие>")
                    continue

                table_name = args[2]
                parts = split_keyword(" ".join(args[3:]), "where")

                if parts is None:
                    print("Не найдено ключевое слово where.")
                    continue

                where_clause = parse_condition(parts[1])
                validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                matching = select(table_data, where_clause, table_name)
                new_data = delete(table_data, where_clause)

                if new_data is None:
                    continue

                if matching:
                    save_table_data(table_name, new_data)
                    clear_select_cache()
                    for record in matching:
                        print(f"Удалена запись: {record}")
                else:
                    print("Записи не найдены.")

            elif command == "info":
                if len(args) != 2:
                    print("Укажите имя таблицы.")
                    continue

                table_name = args[1]

                if table_name not in metadata:
                    print(f'Таблица "{table_name}" не существует.')
                    continue

                print(f"Информация о таблице {table_name}:")
                for column in metadata[table_name]["columns"]:
                    print(f"- {column}")

            else:
                print("Неизвестная команда. Введите help для справки.")

        except (ValueError, SyntaxError) as error:
            print(f"Ошибка: {error}")
