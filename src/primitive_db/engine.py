
import ast
import re
import shlex
from pathlib import Path

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


def parse_value(value):
    value = value.strip()

    if value.lower() == "true":
        return True

    if value.lower() == "false":
        return False

    if value.startswith(("'", '"')):
        result = ast.literal_eval(value)

        if not isinstance(result, str):
            raise ValueError("Ожидалась строка в кавычках.")

        return result

    return int(value)


def split_values(values):
    return re.findall(
        r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|[^,]+""",
        values,
    )


def parse_values(values):
    parts = split_values(values)

    if not parts or any(not part.strip() for part in parts):
        raise ValueError("Некорректный список значений.")

    return [parse_value(part) for part in parts]


def parse_condition(condition):
    parts = condition.split("=", 1)

    if len(parts) != 2:
        raise ValueError("Некорректное условие.")

    column = parts[0].strip()

    if not column:
        raise ValueError("Не указано имя столбца.")

    return {column: parse_value(parts[1])}


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
        user_input = input(">>>Введите команду: ")

        try:
            args = shlex.split(user_input)
        except ValueError:
            print("Некорректное значение. Попробуйте снова.")
            continue

        if not args:
            continue

        command = args[0]

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

                data_file = Path("data") / f"{table_name}.json"
                data_file.unlink(missing_ok=True)

        elif command == "insert":
            match = re.fullmatch(
                r"insert\s+into\s+(\w+)\s+values\s*\((.*)\)",
                user_input.strip(),
                re.IGNORECASE,
            )

            if not match:
                print("Некорректный формат команды insert.")
                continue

            table_name, raw_values = match.groups()

            try:
                values = parse_values(raw_values)
                table_data = load_table_data(table_name)
                new_data = insert(
                    metadata, table_name, values, table_data
                )

                if new_data != table_data:
                    save_table_data(table_name, new_data)

            except (ValueError, SyntaxError) as error:
                print(f"Некорректное значение: {error}")

        elif command == "select":
            match = re.fullmatch(
                r"select\s+from\s+(\w+)"
                r"(?:\s+where\s+(.+))?",
                user_input.strip(),
                re.IGNORECASE,
            )

            if not match:
                print("Некорректный формат команды select.")
                continue

            table_name, raw_condition = match.groups()

            try:
                if table_name not in metadata:
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
            match = re.fullmatch(
                r"update\s+(\w+)\s+set\s+(.+?)\s+where\s+(.+)",
                user_input.strip(),
                re.IGNORECASE,
            )

            if not match:
                print("Некорректный формат команды update.")
                continue

            table_name, raw_set, raw_condition = match.groups()

            try:
                if table_name not in metadata:
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
            match = re.fullmatch(
                r"delete\s+from\s+(\w+)\s+where\s+(.+)",
                user_input.strip(),
                re.IGNORECASE,
            )

            if not match:
                print("Некорректный формат команды delete.")
                continue

            table_name, raw_condition = match.groups()

            try:
                if table_name not in metadata:
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
