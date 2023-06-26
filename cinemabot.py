import datetime
import os
import aiohttp
import sqlite3

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types.message import ContentType

from constants import messages, kinopoisk_search, kinopoisk_api_key, cat_and_cucumber, help_cat, \
    geek_jokes, catboy_image
from search import get_film, get_joke, get_url, get_message


bot = Bot(token=os.environ['BOT_TOKEN'])
dp = Dispatcher(bot)

conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    answer = f"Hello, {message.from_user.first_name}!\n" + messages["START_MSG"]
    await message.reply_photo(cat_and_cucumber, caption=answer, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    await message.reply_photo(help_cat, caption=messages["HELP_MSG"], parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(commands=['history'])
async def send_history(message: types.Message):
    user_id = message.from_user.id
    request = f"SELECT *" \
              f"FROM history " \
              f"WHERE id = '{user_id}' " \
              f"ORDER BY time_of_request DESC"
    cursor.execute(request)
    result = cursor.fetchmany(10)

    msg = "*Last 10 requests:*\n"
    for count, row in enumerate(result):
        msg += f"{count + 1}. {(row[2])}\n"
    await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(commands=['stats'])
async def send_stats(message: types.Message):
    user_id = message.from_user.id
    request = f"SELECT *" \
              f"FROM (" \
                  f"SELECT film_name, count(*) as counter " \
                  f"FROM history " \
                  f"WHERE id = '{user_id}' " \
                  f"GROUP BY film_name" \
              f")" \
              f"ORDER BY counter DESC"
    cursor.execute(request)
    result = cursor.fetchall()

    msg = ""
    for row in result:
        msg += f"*{(row[0])}:* {row[1]}\n"
    await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(commands=['joke'])
async def send_joke(message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(geek_jokes) as resp:
            text = await resp.text()
            status = resp.status
    if status != 200:
        await message.answer("Анекдота не будет. Расходимся!")
        return
    joke = get_joke(text)
    if joke is None:
        await message.answer("Анекдота не будет. Расходимся!")
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(catboy_image) as resp:
            text = await resp.text()
    url = get_url(text)
    msg = f'⚠️WARNING⚠️\nI came up with a joke...\n\n' \
          f"*{joke}*\n"
    if url:
        await message.reply_photo(url, caption=msg, parse_mode=types.ParseMode.MARKDOWN)
        return
    await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler()
async def send_film(message: types.Message) -> None:
    cur_time = datetime.datetime.now().strftime("%Y %m %d, %H:%M:%S")
    user_id = message.from_user.id
    name = message.text

    async with aiohttp.ClientSession(headers={'X-API-KEY': kinopoisk_api_key}) as session:
        async with session.get(kinopoisk_search, params={'keyword': name}) as resp:
            text = await resp.text()
            status = resp.status
    if status != 200:
        await message.answer("Can't find anything... Let's try again with something else?")
        return

    film = get_film(text)
    if film is None:
        await message.answer("Can't find anything... Let's try again with something else?")
        return

    film_n = film['nameRu']
    cursor.execute('INSERT INTO history (id, time_of_request, film_name) VALUES (?, ?, ?)', (user_id, cur_time, film_n))
    conn.commit()

    poster_url, msg = get_message(film)
    await message.reply_photo(poster_url, caption=msg, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(content_types=ContentType.ANY)
async def unknown_message(message: types.Message):
    message_text = f"I don't know what to do with it... 😢\nJust to remember, there is a command:\n /help"
    await message.reply(message_text, parse_mode=types.ParseMode.MARKDOWN)


if __name__ == '__main__':
    executor.start_polling(dp)
    cursor.close()
    conn.close()
