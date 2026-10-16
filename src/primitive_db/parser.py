from primitive_db.constants import VALID_PYTHON_TYPES


def split_keyword(text, keyword):
    """Разделяет строку по ключевому слову вне кавычек."""

    result = []
    current = []
    quote = None
    index = 0

    while index < len(text):
        char = text[index]

        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None

            current.append(char)
            index += 1
            continue

        if quote is None and text.startswith(keyword, index):
            before = text[index - 1] if index > 0 else " "
            after_index = index + len(keyword)
            after = text[after_index] if after_index < len(text) else " "

            if before.isspace() and after.isspace():
                result.append("".join(current).strip())
                result.append(text[after_index:].strip())
                return result

        current.append(char)
        index += 1

    if quote is not None:
        raise ValueError("Незакрытая кавычка.")

    return None


def parse_value(value):
    """Преобразует текстовое значение в значение Python."""

    value = value.strip()
    if not value:
        raise ValueError("Пустое значение.")

    if value[0] in ("'", '"'):
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError("Незакрытая или некорректная строка.")
        inner = value[1:-1]
        if value[0] in inner:
            raise ValueError("Некорректные кавычки в строке.")
        return inner

    if value[-1] in ("'", '"'):
        raise ValueError("Некорректные кавычки в строке.")

    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            "Строковые значения должны быть заключены в кавычки."
        ) from error


def split_values(values):
    """Разделяет значения по запятым вне кавычек."""

    if not values.strip():
        raise ValueError("Список значений не может быть пустым.")

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
            item = "".join(current).strip()

            if not item:
                raise ValueError("Пустое значение между запятыми.")

            result.append(item)
            current = []

        else:
            current.append(char)

    if quote is not None:
        raise ValueError("Незакрытая кавычка.")

    item = "".join(current).strip()

    if not item:
        raise ValueError("После запятой отсутствует значение.")

    result.append(item)
    return result


def parse_values(values):
    """Преобразует текстовый список значений в значения Python."""

    return [parse_value(value) for value in split_values(values)]


def parse_condition(condition):
    """Разбирает условия сравнения через and вне кавычек."""

    parts = []
    current = []
    quote = None
    index = 0

    while index < len(condition):
        char = condition[index]

        if char in ("'", '"'):
            if quote is None:
                quote = char
            elif quote == char:
                quote = None

            current.append(char)
            index += 1
            continue

        if quote is None and condition[index : index + 5] == " and ":
            parts.append("".join(current).strip())
            current = []
            index += 5
            continue

        current.append(char)
        index += 1

    if quote is not None:
        raise ValueError("Незакрытая кавычка.")

    parts.append("".join(current).strip())
    conditions = {}

    for part in parts:
        if "=" not in part:
            raise ValueError("Некорректное условие.")

        column, value = part.split("=", 1)
        column = column.strip()
        value = value.strip()

        if not column or not value:
            raise ValueError("Некорректное условие.")

        if column in conditions:
            raise ValueError(f'Столбец "{column}" указан несколько раз.')

        conditions[column] = parse_value(value)

    return conditions


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

        if column in result:
            raise ValueError(f'Столбец "{column}" указан несколько раз.')

        result[column] = parse_value(value)

    return result


def validate_clause(metadata, table_name, clause, allow_id=True):
    """Проверяет существование таблицы, столбцов и типы значений."""

    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')

    columns = metadata[table_name]["columns"]
    column_types = {
        column.split(":", 1)[0]: column.split(":", 1)[1] for column in columns
    }

    for column, value in clause.items():
        if column not in column_types:
            raise ValueError(f'Столбец "{column}" не существует.')

        if not allow_id and column == "ID":
            raise ValueError("Нельзя изменять или задавать ID вручную.")

        expected_type = VALID_PYTHON_TYPES[column_types[column]]

        if type(value) is not expected_type:
            raise ValueError(f"Некорректный тип значения для столбца {column}.")
