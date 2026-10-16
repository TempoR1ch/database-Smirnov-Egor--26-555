
import time


def handle_db_errors(function):
    """Обрабатывает ожидаемые ошибки операций с базой данных."""

    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (KeyError, ValueError, FileNotFoundError) as error:
            print(f"Ошибка базы данных: {error}")
            return None

    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    return wrapper


def confirm_action(action_name):
    """Создаёт декоратор для подтверждения опасной операции."""

    def decorator(function):
        def wrapper(*args, **kwargs):
            answer = input(
                f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: '
            )

            if answer != "y":
                print("Операция отменена.")
                return None

            return function(*args, **kwargs)

        wrapper.__name__ = function.__name__
        wrapper.__doc__ = function.__doc__
        return wrapper

    return decorator


def log_time(function):
    """Измеряет и выводит время выполнения функции."""

    def wrapper(*args, **kwargs):
        start_time = time.monotonic()

        try:
            return function(*args, **kwargs)
        finally:
            elapsed_time = time.monotonic() - start_time
            print(
                f"Функция {function.__name__} выполнилась "
                f"за {elapsed_time:.3f} секунд"
            )

    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    return wrapper


def create_cacher():
    """Создаёт кеш результатов функций."""

    cache = {}

    def cache_result(key, value_func):
        if key not in cache:
            cache[key] = value_func()

        return cache[key]

    return cache_result
