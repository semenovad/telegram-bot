# Cinema bot [@CherryImpressBot](https://t.me/CherryImpressBot)

Telegram bot, that can help you find movies or TV series, gives brief information about them and sends a link to Kinopoisk.

## Commands, that bot can execute:

To get the description of the film with the characteristics, poster and link send any text message to the bot.

### Other commands: 
**/start** - starting the bot \
**/help** - getting some help info \
**/joke** - a joke with a random image \
**/stats** - searched films statistics \
**/history** - search history (last 10 requests)

## Implementation

The code was written and debugged on a local machine using libraries and APIs, which can be seen below. The code is presented using the functions **cinemabot.py**, **constants.py** and **search.py**. There are 7 handlers and a group of utility functions.

## Libs:
- aiogram 
- sqlite3 (to store user id, request time and request content)
## API:
- kinopoisk api 
- geek-jokes api 
- catboys api 

## Deploy
Yandex Cloud was chosen for the deployment: Yandex CloudFunction + YDB (ydb library instead of sqlite3). Rewrited code is in **deploy.py**.

- ~~sqlite3~~ ---> ydb