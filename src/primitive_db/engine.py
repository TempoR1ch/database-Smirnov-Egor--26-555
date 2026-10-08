from prompt import string


def welcome():
    name = string("Введите ваше имя: ")
    print(f"Привет, {name}!")