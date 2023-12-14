from bs4 import BeautifulSoup
from requests_html import HTMLSession
import re
import datetime
import sqlite3
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Подключение к боту
logging.basicConfig(level=logging.INFO)
bot = Bot(token='')
dispatcher = Dispatcher(bot=bot)


def get_current_date() -> str:
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d")


# Для правильного парсера ежедневного без подписки
def get_current_day_index() -> int:
    return int(get_current_date().split('-')[-1])

#Для красивого деления большого текста в бот
async def send_long_text(user_id, long_text: str):
    max_length = 4096
    # msgs = [long_text[i:i + max_length] for i in range(0, len(long_text), max_length)]
    msgs = long_text.split('\n')
    n = 3
    for i in range(0, len(msgs), n):
        text = '\n'.join(msgs[i:i + n])
        await bot.send_message(user_id, text)


class Reading:
    def __init__(self, title: str, subtitle: str, lines: list[str]):
        self.title = title
        self.subtitle = subtitle
        self.lines = lines

    def get_text(self):
        lines_text = '\n'.join(self.lines)
        return f"{self.title}\n{self.subtitle}\n{lines_text}"

# Парсер Священного писания
def parse_readings() -> list[Reading]:
    session = HTMLSession()
    r = session.get(f'https://azbyka.ru/biblia/days/{get_current_date()}')
    soup = BeautifulSoup(r.html.html, features="lxml")
    raw_readings = soup.select('[id*="reading-"]')
    raw_reading_contents = soup.select('[class*="tbl-content"]')
    result: list[Reading] = []

    for reading_index, raw_reading in enumerate(raw_readings):
        reading_title = raw_reading.find('h2').find(string=True).strip()
        reading_subtitle = raw_reading.find('span', {'class': 'h2-subtitle'}).get_text().strip()
        content = raw_reading_contents[reading_index]
        lines = content.select('[class*="verse lang-r"]')
        numbers = content.select('[class=verse-fullnumber]')
        result_lines: list[str] = []
        for line_index, line in enumerate(lines):
            number = numbers[line_index].get_text()
            result_lines.append(f'{number} {line.text}')
        result.append(Reading(reading_title, reading_subtitle, result_lines))
    return result

# Парсер размышлений об Анеле-Хранителе
def parse_angel_info() -> str:
    session = HTMLSession()
    r = session.get(f'https://azbyka.ru/razmyshleniya-xristianina-ob-angele-xranitele/{get_current_day_index() + 2}')
    soup = BeautifulSoup(r.html.html, features="lxml")
    article = soup.find("div", {"class": "article-single-content main-page-content"})

    title = article.find('h2').get_text()
    article_text = '\n'.join([p.text for p in article.select('p')])
    return f'{title}\n{article_text}'

# Функция отправление подписок
async def send_daily_info():
    connect = sqlite3.connect('base.db')
    with connect:
        cursor = connect.cursor()
        cursor.execute("SELECT cast(id_sv as INTEGER) as id_sv FROM texts")
        ids_ss = [row[0] for row in cursor.fetchall()]
    for ids_ss in ids_ss:
        for r in parse_readings():
            await bot.send_message(ids_ss, r.get_text())

    with connect:
        cursor.execute("SELECT cast(id_a as INTEGER) as id_a FROM angel")
        ids_aa = [row[0] for row in cursor.fetchall()]
    for ids_aa in ids_aa:
        await send_long_text(ids_aa, parse_angel_info())

    cursor.close()
    connect.close()

# Парсер информации о дне
def parse_day_info() -> str:
    session = HTMLSession()
    r = session.get(f'https://azbyka.ru/days/')
    soup = BeautifulSoup(r.html.html, features="lxml")
    calendar_block = soup.find("div", {"id": "calendar"})
    day_info = calendar_block.find("div", {"class": "shadow"}).text.strip()
    event_name = ''
    try:
        event_name = calendar_block.find("b", {"class": "fasting-message"}).text.strip()
    except AttributeError:
        pass
    return f'{day_info}\n{event_name}'


# Парсер размышлений на день
def parse_osnovy() -> str:
    session = HTMLSession()
    r = session.get(f'https://azbyka.ru/days/')
    soup = BeautifulSoup(r.html.html, features="lxml")
    article = soup.find("div", {"id": "osnovy"})
    article_text = '\n'.join([p.text for p in article.select('p')])
    return article_text

# Функция отправления общей информации
async def send_info_for_all():
    connect = sqlite3.connect('base.db')
    with connect:
        cursor = connect.cursor()
        cursor.execute("SELECT cast(id_st as INTEGER) as id_st FROM all_users")
        user_ids = [row[0] for row in cursor.fetchall()]

    for user_id in user_ids:
        await bot.send_message(user_id, parse_day_info().strip())
    for user_id in user_ids:
        await bot.send_message(user_id, parse_osnovy())

    cursor.close()
    connect.close()

# Команды телеграмм бота
@dispatcher.message_handler(commands= 'start')
async def start_messages(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Подписаться")],
        [types.KeyboardButton(text="Отписаться")]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Выберете нужное"
    )
    await message.answer(text="Бот Слово истины - это ваш ежедневный спутник на пути духовного развития и укрепления веры. Присоединяйтесь к нам и начните свой путь к истине!", reply_markup=keyboard)

    #connect base
    connect = sqlite3.connect('base.db')
    cursor = connect.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS all_users(
           id_st INTEGER
       )
       """)
    connect.commit()

    # check exist
    people_id = message.chat.id
    cursor.execute(f"SELECT id_st FROM all_users WHERE id_st = {people_id}")
    data = cursor.fetchone()
    if data is None:
        # Add values
        user_id = [message.chat.id]
        cursor.execute("INSERT INTO all_users VALUES(?);", user_id)
        connect.commit()

    cursor.close()
    connect.close()


@dispatcher.message_handler(lambda message: message.text == "Подписаться")
async def subscribe(message: types.Message):

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Священное писание")
        btn2 = types.KeyboardButton("Размышления об Ангеле-Хранителе")
        back = types.KeyboardButton("Вернуться назад")
        markup.add(btn1)
        markup.add(btn2)
        markup.add(back)
        await message.answer(text="Выберете на что желаете подписаться", reply_markup=markup)


@dispatcher.message_handler(lambda message: message.text == "Священное писание")
async def texta(message: types.Message):
    # connect base
    connect = sqlite3.connect('base.db')
    cursor = connect.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS texts(
        id_sv INTEGER
    )
    """)
    connect.commit()

    # check exist
    people_id = message.chat.id
    cursor.execute(f"SELECT id_sv FROM texts WHERE id_sv = {people_id}")
    data = cursor.fetchone()
    if data is None:
        # Add values
        user_id = [message.chat.id]
        cursor.execute("INSERT INTO texts VALUES(?);", user_id)
        await message.answer("Вы успешанно подписаны.")
        for r in parse_readings():
            await message.answer(r.get_text())
        connect.commit()
    else:
        await message.answer("Вы уже подписаны.")
        connect.commit()

    cursor.close()
    connect.close()


@dispatcher.message_handler(lambda message: message.text == "Размышления об Ангеле-Хранителе")
async def angel(message: types.Message):
    # connect base
    connect = sqlite3.connect('base.db')
    cursor = connect.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS angel(
            id_a INTEGER
        )
        """)
    connect.commit()

    # check exist
    people_id = message.chat.id
    cursor.execute(f"SELECT id_a FROM angel WHERE id_a = {people_id}")
    data = cursor.fetchone()
    if data is None:
        # Add values
        user_id = [message.chat.id]
        cursor.execute("INSERT INTO angel VALUES(?);", user_id)
        await message.answer("Вы успешанно подписаны.")
        await send_long_text(people_id, parse_angel_info())
        connect.commit()
    else:
        await message.answer("Вы уже подписаны.")
        connect.commit()

    cursor.close()
    connect.close()


@dispatcher.message_handler(lambda message: message.text == "Вернуться назад")
async def back(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Подписаться")
    btn2 = types.KeyboardButton("Отписаться")
    markup.add(btn1, btn2)
    await message.answer(text = "Вы вернулись в меню", reply_markup=markup)


@dispatcher.message_handler(lambda message: message.text == "Отписаться")
async def unsubscribe(message: types.Message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("От Священного писания")
    btn2 = types.KeyboardButton("От размышлений об Ангеле-Хранителе")
    back = types.KeyboardButton("Вернуться назад")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(back)
    await message.answer(text="Выберете от какой рассылки желаете отписаться", reply_markup=markup)


@dispatcher.message_handler(lambda message: message.text == "От Священного писания")
async def unsubscribe(message: types.Message):
    # connect to base
    connect = sqlite3.connect('base.db')
    cursor = connect.cursor()
    # delete from base
    people_id = message.chat.id
    cursor.execute(f"SELECT id_sv FROM texts WHERE id_sv = {people_id}")
    data = cursor.fetchone()
    if data is None:
        await message.answer("Вы не были подписаны на рассылку.")
        connect.commit()
    else:
        cursor.execute(f"DELETE FROM texts WHERE id_sv ={people_id}")
        await message.answer("Вы описанны от рассылки.")
        connect.commit()

    cursor.close()
    connect.close()


@dispatcher.message_handler(lambda message: message.text == "От размышлений об Ангеле-Хранителе")
async def unsubscribe(message: types.Message):
    # connect to base
    connect = sqlite3.connect('base.db')
    cursor = connect.cursor()
    # delete from base
    people_id = message.chat.id
    cursor.execute(f"SELECT id_a FROM angel WHERE id_a = {people_id}")
    data = cursor.fetchone()
    if data is None:
        await message.answer("Вы не были подписаны на рассылку.")
        connect.commit()
    else:
        cursor.execute(f"DELETE FROM angel WHERE id_a ={people_id}")
        await message.answer("Вы описанны от рассылки.")
        connect.commit()

    cursor.close()
    connect.close()


async def run_schedule():
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    scheduler.add_job(send_info_for_all, 'cron', hour='05', minute='00')
    scheduler.add_job(send_daily_info, 'cron', hour='06', minute='00')
    scheduler.start()


async def main():
    loop = asyncio.get_event_loop()
    task_1 = loop.create_task(dispatcher.start_polling(bot))
    task_2 = loop.create_task(run_schedule())

    await task_1
    await task_2

#def run_async_legko():
#    loop = asyncio.get_event_loop()
#    asyncio.ensure_future(send_long_text(1, parse_angel_info()))
#    loop.run_forever()
#    loop.close()

if __name__ == "__main__":

    asyncio.run(main())
