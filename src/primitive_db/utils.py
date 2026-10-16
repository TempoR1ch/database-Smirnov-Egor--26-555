import json
import os


def load_metadata(filepath):
    """Загружает метаданные базы данных."""
    try:
        with open(filepath, "r", encoding="utf-8-sig") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_metadata(filepath, data):
    """Сохраняет метаданные базы данных."""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_table_data(table_name):
    """Загружает данные таблицы из JSON-файла."""
    filepath = os.path.join("data", f"{table_name}.json")

    try:
        with open(filepath, "r", encoding="utf-8-sig") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_table_data(table_name, data):
    """Сохраняет данные таблицы в JSON-файл."""
    filepath = os.path.join("data", f"{table_name}.json")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)