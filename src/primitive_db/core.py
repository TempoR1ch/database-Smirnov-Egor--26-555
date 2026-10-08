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