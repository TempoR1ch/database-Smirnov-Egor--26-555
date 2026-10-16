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
    print("\n***Операции с данными***")
    print("Функции:")
    print(
        "<command> insert into <имя_таблицы> "
        "values (<значение1>, <значение2>, ...) - создать запись"
    )
    print(
        "<command> select from <имя_таблицы> "
        "where <столбец> = <значение> - прочитать записи по условию"
    )
    print(
        "<command> select from <имя_таблицы> - прочитать все записи"
    )
    print(
        "<command> update <имя_таблицы> set <столбец> = "
        "<значение> where <столбец> = <значение> - обновить запись"
    )
    print(
        "<command> delete from <имя_таблицы> "
        "where <столбец> = <значение> - удалить запись"
    )
    print("<command> info <имя_таблицы> - информация о таблице")
    print("<command> create_table <имя_таблицы> <столбцы> - создать таблицу")
    print("<command> list_tables - показать все таблицы")
    print("<command> drop_table <имя_таблицы> - удалить таблицу")
    print("<command> help - справочная информация")
    print("<command> exit - выход из программы\n")


def split_keyword(text, keyword):
    position = text.lower().find(keyword.lower())

    if position == -1:
        return None, None

    before = text[:position].strip()
    after = text[position + len(keyword):].strip()

    return before, after


def parse_value(value):
    value = value.strip()

    if value.lower() == "true":
        return True

    if value.lower() == "false":
        return False

    if value.startswith(("'", '"')):
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError("Некорректная строка в кавычках.")

        parsed = shlex.split(value)

        if len(parsed) != 1:
            raise ValueError("Некорректная строка.")

        return parsed[0]

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"Некорректное значение: {value}"
        ) from error


def split_values(values):
    parts = []
    current = []
    quote = None
    escaped = False

    for char in values:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\" and quote is not None:
            current.append(char)
            escaped = True
            continue

        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None

            current.append(char)
            continue

        if char == "," and quote is None:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    if quote is not None:
        raise ValueError("Не закрыты кавычки.")

    parts.append("".join(current).strip())

    return parts


def parse_values(values):
    if not values.strip():
        raise ValueError("Не указаны значения.")

    parts = split_values(values)

    if any(not part for part in parts):
        raise ValueError("Некорректный список значений.")

    return [parse_value(part) for part in parts]


def parse_condition(condition):
    column, separator, value = condition.partition("=")

    if not separator or not column.strip() or not value.strip():
        raise ValueError("Некорректное условие.")

    return {column.strip(): parse_value(value)}


def parse_set_clause(clause):
    result = {}

    for part in split_values(clause):
        condition = parse_condition(part)
        column, value = next(iter(condition.items()))

        if column in result:
            raise ValueError("Столбец указан несколько раз.")

        result[column] = value

    if not result:
        raise ValueError("Не указаны изменения.")

    return result


def validate_clause(metadata, table_name, clause, allow_id=True):
    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')

    column_types = {}

    for column in metadata[table_name]["columns"]:
        name, data_type = column.split(":", 1)
        column_types[name] = data_type

    python_types = {
        "int": int,
        "str": str,
        "bool": bool,
    }

    for column, value in clause.items():
        if column not in column_types:
            raise ValueError(f'Столбца "{column}" не существует.')

        if not allow_id and column == "ID":
            raise ValueError("Нельзя изменять ID записи.")

        expected_type = python_types[column_types[column]]

        if type(value) is not expected_type:
            raise ValueError(
                f"Некорректный тип значения для столбца {column}."
            )


def print_records(metadata, table_name, records):
    columns = [
        column.split(":", 1)[0]
        for column in metadata[table_name]["columns"]
    ]

    table = PrettyTable()
    table.field_names = columns

    for record in records:
        table.add_row([record[column] for column in columns])

    print(table)


def run():
    while True:
        metadata = load_metadata(METADATA_FILE)

        print_help()
        user_input = input(">>>Введите команду: ").strip()

        try:
            args = shlex.split(user_input)
        except ValueError:
            print("Некорректное значение. Попробуйте снова.")
            continue

        if not args:
            continue

        command = args[0].lower()

        if command == "exit":
            if len(args) != 1:
                print("Некорректное значение. Попробуйте снова.")
                continue
            break

        elif command == "help":
            if len(args) != 1:
                print("Некорректное значение. Попробуйте снова.")
            else:
                print_help()

        elif command == "create_table":
            if len(args) < 3:
                print("Некорректное значение. Попробуйте снова.")
                continue

            old_metadata = metadata.copy()
            metadata = create_table(metadata, args[1], args[2:])

            if metadata != old_metadata:
                save_metadata(METADATA_FILE, metadata)

        elif command == "list_tables":
            if len(args) != 1:
                print("Некорректное значение. Попробуйте снова.")
            else:
                list_tables(metadata)

        elif command == "drop_table":
            if len(args) != 2:
                print("Некорректное значение. Попробуйте снова.")
                continue

            table_name = args[1]

            if table_name not in metadata:
                drop_table(metadata, table_name)
                continue

            old_metadata = metadata.copy()
            metadata = drop_table(metadata, table_name)

            if metadata != old_metadata:
                save_metadata(METADATA_FILE, metadata)

                data_file = os.path.join("data", f"{table_name}.json")

                if os.path.exists(data_file):
                    os.remove(data_file)

        elif command == "insert":
            rest = user_input[len(args[0]):].strip()

            if not rest.lower().startswith("into "):
                print("Некорректный формат команды insert.")
                continue

            rest = rest[5:].strip()
            table_name, raw_values = split_keyword(rest, " values ")

            if not table_name or raw_values is None:
                print("Некорректный формат команды insert.")
                continue

            if not raw_values.startswith("(") or not raw_values.endswith(")"):
                print("Некорректный формат команды insert.")
                continue

            try:
                values = parse_values(raw_values[1:-1])
                table_data = load_table_data(table_name)
                new_data = insert(
                    metadata, table_name, values, table_data
                )

                if new_data != table_data:
                    save_table_data(table_name, new_data)

            except (ValueError, SyntaxError) as error:
                print(f"Некорректное значение: {error}")

        elif command == "select":
            rest = user_input[len(args[0]):].strip()

            if not rest.lower().startswith("from "):
                print("Некорректный формат команды select.")
                continue

            rest = rest[5:].strip()
            table_name, raw_condition = split_keyword(rest, " where ")

            if raw_condition is None:
                table_name = rest

            try:
                if not table_name or table_name not in metadata:
                    raise ValueError(
                        f'Таблица "{table_name}" не существует.'
                    )

                where_clause = (
                    parse_condition(raw_condition)
                    if raw_condition is not None
                    else None
                )

                if where_clause is not None:
                    validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                records = select(table_data, where_clause)
                print_records(metadata, table_name, records)

            except (ValueError, SyntaxError) as error:
                print(f"Ошибка: {error}")

        elif command == "update":
            rest = user_input[len(args[0]):].strip()
            table_name, rest = split_keyword(rest, " set ")

            if rest is None:
                print("Некорректный формат команды update.")
                continue

            raw_set, raw_condition = split_keyword(rest, " where ")

            if raw_condition is None:
                print("Некорректный формат команды update.")
                continue

            try:
                if not table_name or table_name not in metadata:
                    raise ValueError(
                        f'Таблица "{table_name}" не существует.'
                    )

                set_clause = parse_set_clause(raw_set)
                where_clause = parse_condition(raw_condition)

                validate_clause(
                    metadata, table_name, set_clause, allow_id=False
                )
                validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                matching = select(table_data, where_clause)
                new_data = update(table_data, set_clause, where_clause)

                if matching:
                    save_table_data(table_name, new_data)

                    for record in matching:
                        print(
                            f'Запись с ID={record["ID"]} в таблице '
                            f'"{table_name}" успешно обновлена.'
                        )
                else:
                    print("Записи не найдены.")

            except (ValueError, SyntaxError) as error:
                print(f"Ошибка: {error}")

        elif command == "delete":
            rest = user_input[len(args[0]):].strip()

            if not rest.lower().startswith("from "):
                print("Некорректный формат команды delete.")
                continue

            rest = rest[5:].strip()
            table_name, raw_condition = split_keyword(rest, " where ")

            if raw_condition is None:
                print("Некорректный формат команды delete.")
                continue

            try:
                if not table_name or table_name not in metadata:
                    raise ValueError(
                        f'Таблица "{table_name}" не существует.'
                    )

                where_clause = parse_condition(raw_condition)
                validate_clause(metadata, table_name, where_clause)

                table_data = load_table_data(table_name)
                matching = select(table_data, where_clause)
                new_data = delete(table_data, where_clause)

                if matching:
                    save_table_data(table_name, new_data)

                    for record in matching:
                        print(
                            f'Запись с ID={record["ID"]} успешно удалена '
                            f'из таблицы "{table_name}".'
                        )
                else:
                    print("Записи не найдены.")

            except (ValueError, SyntaxError) as error:
                print(f"Ошибка: {error}")

        elif command == "info":
            if len(args) != 2:
                print("Некорректное значение. Попробуйте снова.")
                continue

            table_name = args[1]

            if table_name not in metadata:
                print(f'Ошибка: Таблица "{table_name}" не существует.')
                continue

            table_data = load_table_data(table_name)
            columns = ", ".join(metadata[table_name]["columns"])

            print(f"Таблица: {table_name}")
            print(f"Столбцы: {columns}")
            print(f"Количество записей: {len(table_data)}")

        else:
            print(f"Функции {command} нет. Попробуйте снова.")
