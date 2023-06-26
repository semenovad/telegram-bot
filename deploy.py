import os
import aiohttp
import json
import logging
import datetime
import ydb
 
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types.message import ContentType
from aiogram.utils.markdown import text, bold, italic
 
 
driver = ydb.Driver(
    endpoint=os.getenv('YDB_ENDPOINT'), 
    database=os.getenv('YDB_DATABASE')
)
driver.wait(fail_fast=True, timeout=5)
db_session = driver.table_client.session().create()
 
 
messages = {
    "START_MSG": f"My name is Grafinya vishenka\n"
                 f"What film or serial do You want to watch today? 🤔",
    "HELP_MSG":  f"I can help You to find films, serials and some information about them, *just print its name!*\n\n"
                 f"You can also use these commands:\n"
                 f"/history - get 10 last requests\n"
                 f"/stats - get Your request statistics",
    "ERROR_MSG": "Sorry, but I don't know such film or serial 😭"
}
 
# cinema sources
kinopoisk_search = 'https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword'
kinopoisk_api_key = ''
# jokes sources
geek_jokes = 'https://geek-jokes.sameerkumar.website/api?format=json'
catboy_image = 'https://api.catboys.com/img'
 
# photo urls
cat_and_cucumber = f""
help_cat = f""
 
 
# Logger initialization and logging level setting
log = logging.getLogger(__name__)
log.setLevel(os.environ.get('LOGGING_LEVEL', 'INFO').upper())
 
 
def get_film(json_text):
    data = json.loads(json_text)
    log.debug(data)
    if data["films"]:
        result = None
        for film in data["films"]:
            if "nameRu" in film and "description" in film and "countries" in film and "genres" in film:
                log.debug(film)
                return film
    return None
 
 
def get_joke(json_text):
    data = json.loads(json_text)
    if data["joke"]:
        return data["joke"]
    return None
 
 
def get_url(json_text):
    data = json.loads(json_text)
    if data["url"]:
        return data["url"]
    return None
 
 
def get_message(film):
    countries = ", ".join([elem['country'] for elem in film['countries']])
    genres = ", ".join([elem['genre'] for elem in film['genres']])
    message_text = text(
        f"🎥 *{film['nameRu']}*\n\n",
        f"{bold('About film:')}\n{film['description']}\n\n" if "description" in film else "",
        f"{bold('Year of release:')} {film['year']}\n" if "year" in film else "",
        f"{bold('Country:')} {countries}\n",
        f"{bold('Genre:')} {genres}\n",
        f"{bold('Running time:')} {film['filmLength']}\n" if "filmLength" in film else "",
        f"{bold('Kinopoisk:')} {film['rating']}/10\n\n" if ("rating" in film and film["rating"] != "null") else "",
        f"👀 {bold('You can watch it here:')} http://www.kinopoisk.ru/film/{film['filmId']}/",
        sep=''
    )
    if "posterUrl"in film:
        return film["posterUrl"], message_text
    return "", message_text
 
 
# Handlers
async def send_welcome(message: types.Message):
    answer = f"Hello, {message.from_user.first_name}!\n" + messages["START_MSG"]
    await message.reply_photo(cat_and_cucumber, caption=answer, parse_mode=types.ParseMode.MARKDOWN)
 
 
async def send_help(message: types.Message):
    await message.reply_photo(help_cat, caption=messages["HELP_MSG"], parse_mode=types.ParseMode.MARKDOWN)
 
 
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
 
 
async def send_history(message: types.Message):
    user_id = message.from_user.id
 
    query = """
    DECLARE $user_id AS Utf8;
    SELECT *
    FROM history 
    WHERE id = $user_id
    ORDER BY time_of_request DESC
    """
    prepared_query = db_session.prepare(query)
    result_sets = db_session.transaction().execute(
        prepared_query,
        {
            '$user_id': str(user_id),
        },
        commit_tx=True,
    )
 
    log.debug(result_sets)
    msg = "*Last 10 requests:*\n"
    counter = 0
    for row in result_sets[0].rows:
        msg += str(counter + 1) + ". " + str(row.film_name) + "\n"
        counter += 1
        if counter == 10:
            break
 
    await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)
 
 
async def send_stats(message: types.Message):
    user_id = message.from_user.id
 
    query = """
    DECLARE $user_id AS Utf8;
    SELECT *
    FROM (
        SELECT film_name, count(*) AS counter 
        FROM history 
        WHERE id = $user_id
        GROUP BY film_name
    )
    ORDER BY counter DESC
    """
    prepared_query = db_session.prepare(query)
    result_sets = db_session.transaction().execute(
        prepared_query,
        {
            '$user_id': str(user_id),
        },
        commit_tx=True,
    )
 
    log.debug(result_sets)
    msg = "*" + str(message.from_user.first_name) + ", Your stats:*\n\n"
    for row in result_sets[0].rows:
        msg += italic(str(row.film_name)) + ": " + str(row.counter) + "\n"
    
    await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)
 
 
async def send_film(message: types.Message) -> None:
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
 
    cur_time = datetime.datetime.now().strftime("%Y %m %d, %H:%M:%S")
    user_id = message.from_user.id
    film_n = film['nameRu']
    query = """
    DECLARE $user_id AS Utf8;
    DECLARE $cur_time AS Utf8;
    DECLARE $film_n AS Utf8;
    UPSERT INTO history (id, time_of_request, film_name) VALUES
            ($user_id, $cur_time, $film_n);
    """
    prepared_query = db_session.prepare(query)
    db_session.transaction().execute(
        prepared_query,
        {
            '$user_id': str(user_id),
            '$cur_time': str(cur_time),
            '$film_n': str(film_n),
        },
        commit_tx=True,
    )
 
    poster_url, msg = get_message(film)
    try:
        await message.reply_photo(poster_url, caption=msg, parse_mode=types.ParseMode.MARKDOWN)
    except:
        await message.answer(msg, parse_mode=types.ParseMode.MARKDOWN)
 
 
async def unknown_message(message: types.Message):
    message_text = f"I don't know what to do with it... 😢\nJust to remember, there is a command:\n /help"
    await message.reply(message_text, parse_mode=types.ParseMode.MARKDOWN)
 
 
# Functions for Yandex.Cloud
async def register_handlers(dp: Dispatcher):
    """Registration all handlers before processing update."""
 
    dp.register_message_handler(send_welcome, commands=['start'])
    dp.register_message_handler(send_help, commands=['help'])
    dp.register_message_handler(send_joke, commands=['joke'])
    dp.register_message_handler(send_history, commands=['history'])
    dp.register_message_handler(send_stats, commands=['stats'])
    dp.register_message_handler(send_film, content_types=ContentType.TEXT)
    dp.register_message_handler(unknown_message, content_types=ContentType.ANY)
 
    log.debug('Handlers are registered.')
 
 
async def process_event(event, dp: Dispatcher):
    """
    Converting an Yandex.Cloud functions event to an update and
    handling tha update.
    """
 
    update = json.loads(event['body'])
    log.debug('Update: ' + str(update))
 
    Bot.set_current(dp.bot)
    update = types.Update.to_object(update)
    await dp.process_update(update)
 
 
async def handler(event, context):
    """Yandex.Cloud functions handler."""
 
    if event['httpMethod'] == 'POST':
        # Bot and dispatcher initialization
        bot = Bot(os.environ.get('TOKEN'))
        dp = Dispatcher(bot)
 
        await register_handlers(dp)
        await process_event(event, dp)
 
        return {'statusCode': 200, 'body': 'ok'}
    return {'statusCode': 405}