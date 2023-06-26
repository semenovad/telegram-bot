import json
from aiogram.utils.markdown import text, bold

from typing import Dict, List, Tuple, Any


def get_film(json_text: str) -> Dict[Any, Any] | None:
    data: Dict[Any, Any] = json.loads(json_text)
    if data["films"]:
        return data["films"][0]
    return None


def get_joke(json_text: str) -> Dict[Any, Any] | None:
    data: Dict[Any, Any] = json.loads(json_text)
    if data["joke"]:
        return data["joke"]
    return None


def get_url(json_text: str) -> Dict[Any, Any] | None:
    data: Dict[Any, Any] = json.loads(json_text)
    if data["url"]:
        return data["url"]
    return None


def get_message(film: Dict[Any, Any]) -> Tuple[Any, Any]:
    countries = ", ".join([elem['country'] for elem in film['countries']])
    genres = ", ".join([elem['genre'] for elem in film['genres']])
    message_text = text(
        f"🎥 *{film['nameRu']}*\n\n",
        f"{bold('About film:')}\n{film['description']}\n\n",
        f"{bold('Year of release:')} {film['year']}\n" if "year" in film else "",
        f"{bold('Country:')} {countries}\n",
        f"{bold('Genre:')} {genres}\n",
        f"{bold('Running time:')} {film['filmLength']}\n" if "filmLength" in film else "",
        f"{bold('Kinopoisk:')} {film['rating']}/10\n\n" if "rating" in film else "",
        f"👀 {bold('You can watch it here:')} http://www.kinopoisk.ru/film/{film['filmId']}/",
        sep=''
    )
    return film["posterUrl"], message_text
