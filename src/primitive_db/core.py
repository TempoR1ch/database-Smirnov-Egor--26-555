from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data

select_cache = create_cacher()


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Создаёт таблицу и проверяет типы её столбцов."""

    if table_name in metadata:
        print(f'Ошибка: Таблица "{table_name}" уже существует.')
        return metadata

    valid_types = {"int", "str", "bool"}

    for column in columns:
        if ":" not in column:
            print(f"Некорректное значение: {column}. Попробуйте снова.")
            return metadata

        column_name, column_type = column.split(":", 1)

        if not column_name or column_type not in valid_types:
            print(f"Некорректное значение: {column}. Попробуйте снова.")
            return metadata

    columns = ["ID:int"] + columns
    metadata[table_name] = {"columns": columns}

    print(
        f'Таблица "{table_name}" успешно создана '
        f"со столбцами: {', '.join(columns)}"
    )

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
def insert(metadata, table_name, values, table_data=None):
    """Добавляет запись в таблицу."""

    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return table_data if table_data is not None else []

    if table_data is None:
        table_data = load_table_data(table_name)

    columns = metadata[table_name]["columns"]
    user_columns = columns[1:]

    if len(values) != len(user_columns):
        print("Некорректное количество значений.")
        return table_data

    record = {}

    valid_types = {
        "int": int,
        "str": str,
        "bool": bool,
    }

    for column, value in zip(user_columns, values):
        column_name, column_type = column.split(":", 1)

        if type(value) is not valid_types[column_type]:
            print(
                f"Некорректный тип значения "
                f"для столбца {column_name}."
            )
            return table_data

        record[column_name] = value

    record_id = max(
        (row["ID"] for row in table_data),
        default=0,
    ) + 1

    record = {"ID": record_id, **record}
    table_data = table_data + [record]

    print(
        f'Запись с ID={record_id} успешно добавлена '
        f'в таблицу "{table_name}".'
    )

    return table_data


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    """Возвращает записи, соответствующие условию."""

    cache_key = (repr(table_data), repr(where_clause))

    def calculate_result():
        if where_clause is None:
            return table_data

        return [
            row
            for row in table_data
            if all(
                row.get(key) == value
                for key, value in where_clause.items()
            )
        ]

    return select_cache(cache_key, calculate_result)


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Обновляет подходящие записи."""

    updated_data = []

    for row in table_data:
        if all(
            row.get(key) == value
            for key, value in where_clause.items()
        ):
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
        if not all(
            row.get(key) == value
            for key, value in where_clause.items()
        )
    ]
