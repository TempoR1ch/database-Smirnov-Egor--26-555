import os
import shlex

from prettytable import PrettyTable

from primitive_db.core import (
    create_table,
    delete,
    drop_table,
    insert,
    list_tables,
    select,
    update,
)
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)

METADATA_FILE = "db_meta.json"


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


def split_keyword(text, keyword):
    """Разделяет строку по ключевому слову вне кавычек."""
    parts = shlex.split(text, posix=False)
    result = []
    current = []
    found = False

    for part in parts:
        if part.lower() == keyword.lower() and not found:
            result.append(" ".join(current))
            current = []
            found = True
        else:
            current.append(part)

    if not found:
        return None

    result.append(" ".join(current))
    return result


def parse_value(value):
    """Преобразует текстовое значение в Python-тип."""
    value = value.strip()

    if value.lower() == "true":
        return True

    if value.lower() == "false":
        return False

    try:
        return int(value)
    except ValueError:
        return value

def split_values(values):
    """Разделяет значения по запятым вне кавычек."""
    result = []
    current = []
    quote = None

    for char in values:
        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            current.append(char)
        elif char == "," and quote is None:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    if quote is not None:
        raise ValueError("Не закрыты кавычки.")

    if current or values.strip():
        result.append("".join(current).strip())

    return result


def parse_values(values):
    """Преобразует строку значений в список."""
    return [parse_value(value) for value in split_values(values)]


def parse_condition(condition):
    """Разбирает условия сравнения через AND."""
    conditions = []
    parts = condition.split(" AND ")

    for part in parts:
        if "=" not in part:
            raise ValueError("Некорректное условие.")

        column, value = part.split("=", 1)
        column = column.strip()
        value = value.strip()

        if not column or not value:
            raise ValueError("Некорректное условие.")

        conditions.append((column, parse_value(value)))

    return dict(conditions)


def parse_set_clause(clause):
    """Разбирает значения для команды update."""
    result = {}

    for part in split_values(clause):
        if "=" not in part:
            raise ValueError("Некорректный SET.")

        column, value = part.split("=", 1)
        column = column.strip()
        value = value.strip()

        if not column or not value:
            raise ValueError("Некорректный SET.")

        result[column] = parse_value(value)

    return result


def validate_clause(metadata, table_name, clause, allow_id=True):
    """Проверяет существование таблицы и указанных столбцов."""
    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')

    columns = metadata[table_name]["columns"]
    column_names = [column.split(":", 1)[0] for column in columns]

    for column in clause:
        if column not in column_names:
            raise ValueError(f'Столбец "{column}" не существует.')

        if not allow_id and column == "ID":
            raise ValueError("Нельзя изменять или задавать ID вручную.")


def print_records(metadata, table_name, records):
    """Выводит записи таблицы в виде таблицы."""
    if table_name not in metadata:
        print(f'Таблица "{table_name}" не существует.')
        return

    if not records:
        print("Записи не найдены.")
        return

    table = PrettyTable()
    columns = [
        column.split(":", 1)[0]
        for column in metadata[table_name]["columns"]
    ]
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

            args = shlex.split(command_line)
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
                    data_file = os.path.join("data", f"{table_name}.json")

                    if os.path.exists(data_file):
                        os.remove(data_file)

            elif command == "insert":
                if len(args) < 5 or args[1].lower() != "into":
                    print("Использование: insert into <таблица> values (...)")
                    continue

                table_name = args[2]

                if args[3].lower() != "values":
                    print("Ожидается ключевое слово values.")
                    continue

                values_text = " ".join(args[4:]).strip()

                if not values_text.startswith("(") or not values_text.endswith(")"):
                    print("Значения должны быть заключены в скобки.")
                    continue

                values = parse_values(values_text[1:-1])
                table_data = load_table_data(table_name)
                new_data = insert(metadata, table_name, values, table_data)

                if new_data is not None and new_data != table_data:
                    save_table_data(table_name, new_data)

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
                records = select(table_data, where_clause)

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
                matching = select(table_data, where_clause)

                if not matching:
                    print("Записи не найдены.")
                    continue

                new_data = update(table_data, set_clause, where_clause)

                if new_data is not None:
                    save_table_data(table_name, new_data)
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
                matching = select(table_data, where_clause)
                new_data = delete(table_data, where_clause)

                if new_data is None:
                    continue

                if matching:
                    save_table_data(table_name, new_data)
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
