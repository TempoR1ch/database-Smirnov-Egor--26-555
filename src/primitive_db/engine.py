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
list_tables - вывести список таблиц
drop_table <имя_таблицы> - удалить таблицу (с подтверждением)
insert into <имя_таблицы> values (<значение1>, ...) - добавить запись
select from <имя_таблицы> [where <условие>] - прочитать записи
update <имя_таблицы> set <столбец>=<значение> where <условие> - обновить записи
delete from <имя_таблицы> where <условие> - удалить записи (с подтверждением)
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


def extract_insert_values(values_text):
    """Проверяет скобки и извлекает одну группу значений insert."""
    if not values_text.startswith("(") or not values_text.endswith(")"):
        raise ValueError("Некорректное значение: ожидается одна группа в скобках.")

    quote = None
    depth = 0

    for index, char in enumerate(values_text):
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue

        if quote is not None:
            continue

        if char == "(":
            depth += 1

            if depth > 1:
                raise ValueError("Некорректное значение: лишние скобки.")

        elif char == ")":
            depth -= 1

            if depth < 0:
                raise ValueError("Некорректное значение: лишние скобки.")

            if depth == 0 and index != len(values_text) - 1:
                raise ValueError("Некорректное значение: лишние аргументы.")

    if quote is not None or depth != 0:
        raise ValueError("Некорректное значение: проверьте кавычки и скобки.")

    return values_text[1:-1]


def run():
    """Запускает интерактивную оболочку базы данных."""
    metadata = load_metadata(METADATA_FILE)

    while True:
        try:
            command_line = input("Введите команду: ").strip()

            if not command_line:
                continue

            args = shlex.split(command_line, posix=False)
            command = args[0]

            if command == "help":
                if len(args) != 1:
                    raise ValueError(
                        "Некорректное значение: help не принимает аргументы."
                    )
                print_help()

            elif command == "exit":
                if len(args) != 1:
                    raise ValueError(
                        "Некорректное значение: exit не принимает аргументы."
                    )
                print("Работа завершена.")
                break

            elif command == "list_tables":
                if len(args) != 1:
                    raise ValueError(
                        "Некорректное значение: list_tables не принимает аргументы."
                    )
                list_tables(metadata)

            elif command == "create_table":
                if len(args) < 3:
                    raise ValueError(
                        "Некорректное значение: укажите таблицу и хотя бы один столбец."
                    )

                table_name = args[1]
                columns = args[2:]
                old_metadata = metadata.copy()
                new_metadata = create_table(metadata, table_name, columns)

                if new_metadata is not None:
                    metadata = new_metadata

                    if metadata != old_metadata:
                        save_metadata(METADATA_FILE, metadata)

            elif command == "drop_table":
                if len(args) != 2:
                    raise ValueError(
                        "Некорректное значение: drop_table принимает имя таблицы."
                    )

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
                if len(args) < 5 or args[1] != "into" or args[3] != "values":
                    raise ValueError(
                        "Некорректное значение: используйте "
                        "insert into <таблица> values (<значения>)."
                    )

                table_name = args[2]
                values_text = " ".join(args[4:]).strip()
                values = parse_values(extract_insert_values(values_text))
                table_data = load_table_data(table_name)
                new_data = insert(metadata, table_name, table_data, values)

                if new_data is not None and new_data != table_data:
                    save_table_data(table_name, new_data)
                    clear_select_cache()

            elif command == "select":
                if len(args) < 3 or args[1] != "from":
                    raise ValueError(
                        "Некорректное значение: используйте "
                        "select from <таблица> [where <условие>]."
                    )

                table_name = args[2]

                if table_name not in metadata:
                    print(f'Ошибка: Таблица "{table_name}" не существует.')
                    continue

                rest = " ".join(args[3:]).strip()
                where_clause = None

                if rest:
                    where_parts = split_keyword(rest, "where")

                    if where_parts is None or where_parts[0]:
                        raise ValueError(
                            "Некорректное значение: используйте where <условие>."
                        )

                    if not where_parts[1]:
                        raise ValueError("Некорректное значение: условие where пустое.")

                    if split_keyword(where_parts[1], "where") is not None:
                        raise ValueError("Некорректное значение: лишнее where.")

                    where_clause = parse_condition(where_parts[1])
                    validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                records = select(table_data, where_clause, table_name)

                if records is not None:
                    print_records(metadata, table_name, records)

            elif command == "update":
                if len(args) < 6 or args[2] != "set":
                    raise ValueError(
                        "Некорректное значение: используйте "
                        "update <таблица> set <столбец>=<значение> "
                        "where <условие>."
                    )

                table_name = args[1]
                rest = " ".join(args[3:]).strip()
                set_parts = split_keyword(rest, "where")

                if set_parts is None or not set_parts[0] or not set_parts[1]:
                    raise ValueError(
                        "Некорректное значение: update требует set и where."
                    )

                if split_keyword(set_parts[0], "where") is not None:
                    raise ValueError("Некорректное значение: лишнее where.")

                if split_keyword(set_parts[0], "set") is not None:
                    raise ValueError("Некорректное значение: лишнее set.")

                if split_keyword(set_parts[1], "where") is not None:
                    raise ValueError("Некорректное значение: лишнее where.")

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
                    for record in matching:
                        print(f"Запись с ID={record['ID']} успешно обновлена.")

            elif command == "delete":
                if len(args) < 5 or args[1] != "from":
                    raise ValueError(
                        "Некорректное значение: используйте "
                        "delete from <таблица> where <условие>."
                    )

                table_name = args[2]
                rest = " ".join(args[3:]).strip()
                where_parts = split_keyword(rest, "where")

                if where_parts is None or where_parts[0]:
                    raise ValueError(
                        "Некорректное значение: используйте where <условие>."
                    )

                if not where_parts[1]:
                    raise ValueError("Некорректное значение: условие where пустое.")

                if split_keyword(where_parts[1], "where") is not None:
                    raise ValueError("Некорректное значение: лишнее where.")

                where_clause = parse_condition(where_parts[1])
                validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                matching = select(table_data, where_clause, table_name)

                if not matching:
                    print("Записи не найдены.")
                    continue

                new_data = delete(table_data, where_clause)

                if new_data is None:
                    continue

                save_table_data(table_name, new_data)
                clear_select_cache()

                for record in matching:
                    print(f"Запись с ID={record['ID']} успешно удалена.")

            elif command == "info":
                if len(args) != 2:
                    raise ValueError(
                        "Некорректное значение: info принимает имя таблицы."
                    )

                table_name = args[1]

                if table_name not in metadata:
                    print(f'Ошибка: Таблица "{table_name}" не существует.')
                    continue

                print(f"Информация о таблице {table_name}:")
                for column in metadata[table_name]["columns"]:
                    print(f"- {column}")

            else:
                print("Неизвестная команда. Введите help для справки.")

        except (ValueError, SyntaxError) as error:
            print(f"Ошибка: {error}")
