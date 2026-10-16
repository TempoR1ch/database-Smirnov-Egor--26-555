import shlex


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
    """Convert a textual value to a Python type."""
    value = value.strip()

    if not value:
        raise ValueError("Empty value.")

    if value.lower() == "true":
        return True

    if value.lower() == "false":
        return False

    if value[0] in ("'", '"'):
        if len(value) < 2 or value[-1] != value[0]:
            raise ValueError("Unclosed or invalid string.")
        return value[1:-1]

    if value[-1] in ("'", '"'):
        raise ValueError("Invalid quoted string.")

    try:
        return int(value)
    except ValueError:
        raise ValueError("String values must be enclosed in quotes.")


def split_values(values):
    """Split values by commas outside quotes."""
    if not values.strip():
        raise ValueError("Values cannot be empty.")

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
                raise ValueError("Empty value between commas.")
            result.append(item)
            current = []
        else:
            current.append(char)

    if quote is not None:
        raise ValueError("Unclosed quote.")

    item = "".join(current).strip()
    if not item:
        raise ValueError("Empty value after comma.")

    result.append(item)
    return result


def parse_values(values):
    """Convert a textual list of values to Python values."""
    return [parse_value(value) for value in split_values(values)]


def parse_condition(condition):
    """Разбирает условия сравнения через AND вне кавычек."""
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

        if quote is None and condition[index : index + 5].upper() == " AND ":
            parts.append("".join(current).strip())
            current = []
            index += 5
            continue

        current.append(char)
        index += 1

    if quote is not None:
        raise ValueError("Unclosed quote.")

    parts.append("".join(current).strip())

    conditions = []

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
