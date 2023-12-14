from bs4 import BeautifulSoup
from requests_html import HTMLSession
import re
import datetime
import sqlite3
import asyncio
import logging
from aiogram import Bot, Dispatcher, types

logging.basicConfig(level=logging.INFO)
bot = Bot(token='')
dispatcher = Dispatcher(bot=bot)

def get_current_date() -> str:
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d")

class Reading:
    def __init__(self, title: str, lines: list[str]):
        self.title = title
        self.lines = lines

    def get_text(self):
        lines_text = '\n--'.join(self.lines)
        return f"{self.title}\n{lines_text}"

def parse_readings() -> list[Reading]:
    session = HTMLSession()
    r = session.get(f'https://azbyka.ru/biblia/days/{get_current_date()}')
    soup = BeautifulSoup(r.html.html)
    raw_readings = soup.select('[id*="reading-"]')
    raw_reading_contents = soup.select('[class*="tbl-content"]')
    result: list[Reading] = []

    for i, raw_reading in enumerate(raw_readings):
        reading_title = re.sub(' +', ' ', raw_reading.text.replace("\n", ""))
        content = raw_reading_contents[i]
        lines = content.select('[class*="verse lang-r"]')
        result_lines: list[str] = []
        for line in lines:
            result_lines.append(line.text)
        result.append(Reading(reading_title, result_lines))

    return result

for r in parse_readings():
    print(r.get_text())
    print()

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


@dispatcher.message_handler(lambda message: message.text == "Подписаться")
async def subscribe(message: types.Message):

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        #в столбец
        btn1 = types.KeyboardButton("Священное писание")
        btn2 = types.KeyboardButton("Размышления об Ангеле-Хранителе")
        back = types.KeyboardButton("Вернуться назад")
        markup.add(btn1)
        markup.add(btn2)
        markup.add(back)
        await message.answer(text="Выберете на что желаете подписаться", reply_markup=markup)

@dispatcher.message_handler(lambda message: message.text == "Священное писание")
async def texta(message: types.Message):
        #connect base
        connect = sqlite3.connect('users.db')
        cursor = connect.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER
        )
        """)
        connect.commit()

        #check exist
        people_id = message.chat.id
        cursor.execute(f"SELECT id FROM users WHERE id = {people_id}")
        data = cursor.fetchone()
        if data is None:
            #Add values
            user_id = [message.chat.id]
            cursor.execute("INSERT INTO users VALUES(?);", user_id)
            await message.answer("Вы успешанно подписаны.")
            #bot.send_message(message.chat.id, "Вы успешанно подписаны на рассылку писаний.")
            for r in parse_readings():
                await message.answer(r.get_text())
                #bot.send_message(message.chat.id, r.get_text())
            connect.commit()
        else:
            await message.answer("Вы уже подписаны.")
            #bot.send_message(message.chat.id, 'Вы уже подписанны на рассылку писаний.')
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
    #connect to base
        connect = sqlite3.connect('users.db')
        cursor = connect.cursor()
        #delete from base
        people_id = message.chat.id
        cursor.execute(f"SELECT id FROM users WHERE id = {people_id}")
        data = cursor.fetchone()
        if data is None:
            await message.answer("Вы не были подписаны на рассылку.")
            connect.commit()
        else:
            cursor.execute(f"DELETE FROM users WHERE id={people_id}")
            await message.answer("Вы описанны от рассылки.")
            connect.commit()

        cursor.close()
        connect.close()

async def main():
    await dispatcher.start_polling(bot)

if __name__ == "__main__" :
    asyncio.run(main())