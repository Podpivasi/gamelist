"""Модуль для main файла с функциями"""
import asyncio
import re
import sqlite3
import pandas as pd
import aiohttp

def check_rating():
    "Если оценка не входит в диапазон от 1 до 10 - выодит ошибку"
    my_rating = input("\nПоставьте оценку игре от 1 до 10: ")
    while True:
        if not my_rating:
            return None
        if not my_rating.isdigit():
            my_rating = input(f"\n{my_rating} - неверный символ!\n\nВведите оценку от 1 до 10: ")
        elif int(my_rating) <= 0 or int(my_rating) > 10:
            my_rating = input(f"\n{my_rating} - неверное число!\n\nВведите оценку от 1 до 10: ")
        else:
            return int(my_rating)

def create_list():
    "Если базы данных не существует, то создает её"
    with sqlite3.connect("my_list.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                title           TEXT        NOT NULL,
                genre           TEXT,
                platform        TEXT,
                release_date    TEXT,
                my_rating       INTEGER,
                notes           TEXT
            )
        """)
    conn.close()

def check_list(game):
    "Проверяет есть ли уже в личном списке игра"
    with sqlite3.connect("my_list.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor_1 = conn.cursor()
        cursor_1.execute("SELECT title FROM games")
        result = any(row["title"] == game["title"] for row in cursor_1.fetchall())
    conn.close()
    return result

class Game:
    "Класс для создания шаблона рейтига игр"

    def __init__(self, title, genre, platform, release_date, my_rating, notes):
        self.title = title
        self.genre = genre
        self.platform = platform
        self.release_date = release_date
        self.my_rating = my_rating
        self.notes = notes

    def append_info(self):
        "Выводит, что игра уже добавлена, если она уже есть в списке"
        return f"{self.title} добавлена в ваш список"

    def info(self):
        "Выводит информацию об игре после шаблона"
        return (
            f"Название: {self.title}, Жанр: {self.genre}, Платформа: {self.platform}, "
            f"Дата релиза: {self.release_date}, Оценка: {self.my_rating}, Заметки: {self.notes}"
        )

    def insert_in_list(self):
        "Добавляет в личный список информацию о выбранной игре"
        with sqlite3.connect("my_list.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO games (title, genre, platform, release_date, my_rating, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.title,
                    self.genre,
                    self.platform,
                    self.release_date,
                    self.my_rating,
                    self.notes
                ))
        conn.close()

async def get_data(url):
    "Открывает ссылку и возвращает данные"
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                return await response.json()
    except aiohttp.ClientConnectorError as e:
        print(f"Ошибка: {e}. Не удалось подключиться к серверу")
        return
    except asyncio.TimeoutError:
        print("Превышено время ожидания ответа от сервера")
        return
    except aiohttp.ClientResponseError as e:
        print(f"Ошибка: {e}")
        return

def search_in_data(data, choice):
    "Ищет в data совпадения с введеным названием, если их много дает выбрать из списка совпадений"
    found_in_data = []
    for i in data:
        search_title = re.search(rf"{re.escape(choice)}", i["title"])
        if search_title is not None:
            found_in_data.append(i)
    if len(found_in_data) > 1:
        for index, item in enumerate(found_in_data, start=1):
            print(f"{index}. {item['title']}")
        total_matches = input("\nНашлось несколько совпадений, введите цифру нужной игры: ")
        while True:
            if not total_matches:
                return None
            if total_matches.isdigit() and 0 < int(total_matches) <= len(found_in_data):
                return found_in_data[int(total_matches) - 1]
            total_matches = input(
                "\nНекорректная цифра или символ!"
                "\n\nВведите цифру нужной игры: "
            )
    elif len(found_in_data) == 1:
        return found_in_data[0]
    print("\nТакой игры нет")
    return None

def data_to_class(url):
    "Преобразует полученные с ссылки данные в шаблон класса Game "
    data = asyncio.run(get_data(url))
    if data is None:
        return
    for i in data:
        print(i["title"])
    choice = input(
        "\nНапишите название игры, чтобы добавить ее в ваш список"
        """\nили нажмите Enter, чтобы вернуться в меню: \n"""
    )
    create_list()
    while choice:
        selected_game = search_in_data(data, choice)
        if selected_game:
            found_in_list = check_list(selected_game)
            if found_in_list:
                print(f"\n{selected_game['title']} уже есть в вашем списке")
            else:
                rating = check_rating()
                if rating:
                    note = input("\nВведите заметку по игре (опционально):\n")
                    game_info = Game(
                        selected_game["title"],
                        selected_game["genre"],
                        selected_game["platform"],
                        selected_game["release_date"],
                        rating,
                        note
                        )
                    game_info.insert_in_list()
                    print(game_info.append_info())
        choice = input(
            "\nНапишите название игры"
            """\nили нажмите Enter, чтобы вернуться в меню: """
            )

def sort_list():
    "Сортировка личного списка по столбцу"
    create_list()
    with sqlite3.connect("my_list.db") as conn:
        df = pd.read_sql("SELECT * FROM games", conn)
    conn.close()
    if df.empty:
        print("\nВаш список пуст, сортировать нечего.")
        input("\nНажмите Enter, чтобы вернуться в меню...")
        return
    while True:
        print(
            "\nВыберите колонку для сортировки:"
            "\n1. По названию"
            "\n2. По жанру"
            "\n3. По рейтингу"
            "\n4. Выход в меню"
        )
        colomn_num = input("\nВведите цифру: ")
        if not colomn_num.isdigit():
            print("\nНеверный символ! Попробуйте еще раз.")
            continue
        if int(colomn_num) == 1:
            colomn = "title"
        elif int(colomn_num) == 2:
            colomn = "genre"
        elif int(colomn_num) == 3:
            colomn = "my_rating"
        elif int(colomn_num) == 4:
            return
        else:
            print("\nНеверное число! Попробуйте еще раз.")
            continue
        while True:
            acd_desc_num = input(
                "\nТип сортировки:"
                "\n1. По убыванию"
                "\n2. По возрастанию"
                "\n3. Выход в меню"
                "\nВведите цифру: "
            )
            if not acd_desc_num.isdigit():
                print("\nНеверный символ! Попробуйте еще раз.")
                continue
            if int(acd_desc_num) == 1:
                acd_desc = False
            elif int(acd_desc_num) == 2:
                acd_desc = True
            elif int(acd_desc_num) == 3:
                return
            else:
                print("\nНеверное число! Попробуйте еще раз.")
                continue
            print(df.sort_values(colomn, ascending=acd_desc))
            input("\nНажмите Enter, чтобы вернуться в меню...")
            return

def statistic():
    "Выводит статистику по личному списку игр"
    create_list()
    with sqlite3.connect("my_list.db") as conn:
        df = pd.read_sql("SELECT * FROM games", conn)
    conn.close()
    if df.empty:
        print("Список пуст, добавьте игры")
        input("\nНажмите Enter, чтобы вернуться в меню...")
        return
    while True:
        years = input(
            "Введите за последние сколько лет "
            "вы хотите увидеть статистику (целое число): "
            )
        if years.isdigit() and int(years) > 0:
            df["release_date"] = pd.to_datetime(df["release_date"])
            years_ago = pd.Timestamp.now() - pd.DateOffset(years=int(years))
            df = df[df["release_date"] >= years_ago]
            if df.empty:
                print("\nЗа этот интервал нет игр")
                input("\nНажмите Enter, чтобы вернуться в меню...")
                return
            print(f"\nСредний рейтинг по всей коллекции: {df['my_rating'].mean()}")
            print("Количество игр по каждому жанру:")
            genre_counts = df["genre"].value_counts()
            for x, y in genre_counts.items():
                print(f"    {x}: {y}")
            print("Средний рейтинг по жанру:")
            avg_by_genre = df.groupby("genre")["my_rating"].mean()
            for x, y in avg_by_genre.items():
                print(f"    {x}: {round(y, 1)}")
            print("Количество игр по платформе:")
            #platform_counts = df.groupby("platform").size()
            platform_counts = df['platform'].value_counts()
            for x, y in platform_counts.items():
                print(f"    {x}: {y}")
            max_rating = df["my_rating"].max()
            print(f"Лучшие игры по оценке: {max_rating}")
            top_games = df[df["my_rating"] == max_rating]
            for _, row in top_games.iterrows(): # можно через to_list()
                print(f"    {row['title']}")
            min_rating = df["my_rating"].min()
            print(f"Худшие игры по оценке: {min_rating}")
            low_rating = df[df["my_rating"] == min_rating]
            for row in low_rating["title"].to_list(): # можно через iterrows()
                print(f"    {row}")
            min_date = df["release_date"].min()
            oldest = df[df["release_date"] == min_date]
            for _, row in oldest.iterrows():
                print(
                    f"Самая старая игра в коллекции:"
                    f"\n{row['title']} - {row['release_date'].strftime('%d.%m.%Y')}"
                )
            max_date = df["release_date"].max()
            newest = df[df["release_date"] == max_date]
            for _, row in newest.iterrows():
                print(
                    f"Самая новая игра в коллекции:"
                    f"\n{row['title']} - {row['release_date'].strftime('%d.%m.%Y')}"
                )
            print(f"Общее количество игр в списке: {df['title'].count()}")
            input("\nНажмите Enter, чтобы вернуться в меню...")
            return
        if years == "":
            return
        print("\nНеверный символ! Попробуйте еще раз.")

def delete_from_list():
    "Удаляет игру из личного списка"
    with sqlite3.connect("my_list.db") as conn:
        df = pd.read_sql("SELECT title FROM games", conn)
    conn.close()
    if df.empty:
        print("\nВаш список пуст, удалять нечего.")
        return
    titles = df["title"].tolist()
    for index, title in enumerate(titles, start=1):
        print(f"{index}. {title}")
    while True:
        number = input("\nВведите цифру игры для удаления или нажмите Enter, чтобы выйти: ")
        if not number:
            return
        if number.isdigit() and 0 < int(number) <= len(titles):
            selected_title = titles[int(number) - 1]
            with sqlite3.connect("my_list.db") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM games WHERE title = ?", (selected_title,))
            conn.close()
            print(f"\n{selected_title} удалена из вашего списка")
            return
        print("\nНекорректная цифра или символ!")

def menu(url):
    "Меню с выбором функций"
    while True:
        print(
            "\nМеню:"
            "\n1. Добавить игру в личный список"
            "\n2. Вывести личный список"
            "\n3. Сортировать личный список"
            "\n4. Статистика по личному списку"
            "\n5. Удалить игру из списка"
        )
        number = input("\nВведите цифру или нажмите Enter, чтобы выйти: ")
        if number == "":
            return
        if not number.isdigit():
            print("\nНеверный символ! Попробуйте еще раз.")
        elif int(number) == 1:
            data_to_class(url)
        elif int(number) == 2:
            create_list()
            with sqlite3.connect("my_list.db") as conn:
                df = pd.read_sql("SELECT * FROM games", conn)
            conn.close()
            if df.empty:
                print("\nВаш список пуст.")
                input("\nНажмите Enter, чтобы вернуться в меню...")
            else:
                print(df)
                input("\nНажмите Enter, чтобы вернуться в меню...")
        elif int(number) == 3:
            sort_list()
        elif int(number) == 4:
            statistic()
        elif int(number) == 5:
            delete_from_list()
        else:
            print("\nНеверное число! Попробуйте еще раз.")

if __name__ == "__main__":
    menu("https://www.freetogame.com/api/games")
