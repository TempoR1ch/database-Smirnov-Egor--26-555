from primitive_db.constants import VALID_COLUMN_TYPES, VALID_PYTHON_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)

select_cache = create_cacher()


def clear_select_cache():
    """Очищает кеш результатов select."""
    select_cache.clear()


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Создаёт таблицу и проверяет типы её столбцов."""

    if (
        not table_name
        or not table_name.isascii()
        or not table_name.replace("_", "").isalnum()
    ):
        print(
            "Некорректное имя таблицы. "
            "Используйте латинские буквы, цифры и подчёркивание."
        )
        return metadata

    if table_name in metadata:
        print(f'Ошибка: Таблица "{table_name}" уже существует.')
        return metadata

    column_names = set()

    for column in columns:
        if ":" not in column:
            print(f"Некорректное значение: {column}. Попробуйте снова.")
            return metadata

        column_name, column_type = column.split(":", 1)

        if (
            not column_name
            or column_type not in VALID_COLUMN_TYPES
            or column_name.upper() == "ID"
            or column_name in column_names
        ):
            print(f"Некорректное значение: {column}. Попробуйте снова.")
            return metadata

        column_names.add(column_name)

    columns = ["ID:int"] + columns
    metadata[table_name] = {"columns": columns}

    print(f'Таблица "{table_name}" успешно создана со столбцами: {", ".join(columns)}')

    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удаляет таблицу из метаданных."""

    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return metadata

    del metadata[table_name]

    print(f'Таблица "{table_name}" успешно удалена.')

    return metadata


@handle_db_errors
def list_tables(metadata):
    """Выводит список таблиц."""

    for table_name in metadata:
        print(f"- {table_name}")


@handle_db_errors
@log_time
def insert(metadata, table_name, table_data, values):
    """Добавляет запись в таблицу."""

    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return table_data if table_data is not None else []

    columns = metadata[table_name]["columns"]
    user_columns = columns[1:]

    if len(values) != len(user_columns):
        print("Некорректное количество значений.")
        return table_data

    record = {}

    for column, value in zip(user_columns, values):
        column_name, column_type = column.split(":", 1)

        if type(value) is not VALID_PYTHON_TYPES[column_type]:
            print(f"Некорректный тип значения для столбца {column_name}.")
            return table_data

        record[column_name] = value

    record_id = max((row["ID"] for row in table_data), default=0) + 1
    record = {"ID": record_id, **record}
    table_data = table_data + [record]

    print(f'Запись с ID={record_id} успешно добавлена в таблицу "{table_name}".')

    return table_data


@handle_db_errors
@log_time
def select(table_data, where_clause=None, table_name=None):
    """Возвращает записи, соответствующие условию."""

    cache_key = (table_name, repr(table_data), repr(where_clause))

    def calculate_result():
        if where_clause is None:
            return table_data

        return [
            row
            for row in table_data
            if all(row.get(key) == value for key, value in where_clause.items())
        ]

    return select_cache(cache_key, calculate_result)


@handle_db_errors
def update(table_data, set_clause, where_clause, metadata=None, table_name=None):
    """Обновляет подходящие записи."""

    if metadata is not None and table_name is not None:
        if table_name not in metadata:
            raise ValueError(f'Таблица "{table_name}" не существует.')

        columns = metadata[table_name]["columns"]
        column_types = {
            column.split(":", 1)[0]: column.split(":", 1)[1] for column in columns
        }

        for column, value in set_clause.items():
            if column == "ID":
                raise ValueError("Нельзя изменять столбец ID.")

            if column not in column_types:
                raise ValueError(f'Столбец "{column}" не существует.')

            expected_type = VALID_PYTHON_TYPES[column_types[column]]
            if type(value) is not expected_type:
                raise ValueError(f"Некорректный тип значения для столбца {column}.")

    updated_data = []

    for row in table_data:
        if all(row.get(key) == value for key, value in where_clause.items()):
            row = {**row, **set_clause}

        updated_data.append(row)

    return updated_data


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause):
    """Удаляет записи, соответствующие условию."""

    return [
        row
        for row in table_data
        if not all(row.get(key) == value for key, value in where_clause.items())
    ]
