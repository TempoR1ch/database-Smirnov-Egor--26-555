
def create_table(metadata, table_name, columns):
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


def drop_table(metadata, table_name):
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return metadata

    del metadata[table_name]

    print(f'Таблица "{table_name}" успешно удалена.')

    return metadata


def list_tables(metadata):
    for table_name in metadata:
        print(f"- {table_name}")


def insert(metadata, table_name, values, table_data=None):
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return table_data if table_data is not None else []

    if table_data is None:
        from primitive_db.utils import load_table_data

        table_data = load_table_data(table_name)

    columns = metadata[table_name]["columns"]
    user_columns = columns[1:]

    if len(values) != len(user_columns):
        print("Некорректное количество значений.")
        return table_data

    record = {}

    for column, value in zip(user_columns, values):
        column_name, column_type = column.split(":", 1)

        valid_types = {
            "int": int,
            "str": str,
            "bool": bool,
        }

        if type(value) is not valid_types[column_type]:
            print(f"Некорректный тип значения для столбца {column_name}.")
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


def select(table_data, where_clause=None):
    if where_clause is None:
        return table_data

    return [
        row
        for row in table_data
        if all(row.get(key) == value for key, value in where_clause.items())
    ]


def update(table_data, set_clause, where_clause):
    updated_data = []

    for row in table_data:
        if all(
            row.get(key) == value
            for key, value in where_clause.items()
        ):
            row = {**row, **set_clause}

        updated_data.append(row)

    return updated_data


def delete(table_data, where_clause):
    return [
        row
        for row in table_data
        if not all(
            row.get(key) == value
            for key, value in where_clause.items()
        )
    ]
