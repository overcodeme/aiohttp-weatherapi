from aiologger.loggers.json import JsonLogger
from aiologger.handlers.files import AsyncFileHandler
from aiohttp import ClientSession, web
import asyncio
import json
from datetime import datetime
import aiosqlite


storage = {}

logger = JsonLogger(level=10)
file_handler = AsyncFileHandler(filename='app.log')
logger.add_handler(file_handler)  # Добавляем обработчик записи в файл


async def create_table():
    async with aiosqlite.connect('weather.db') as db:
        await db.execute('CREATE TABLE IF NOT EXISTS weather_data'
                         '(date text, city text, weather text)')
        await db.commit()


async def save_to_db(city, weather):
    async with aiosqlite.connect('weather.db') as db:
        await db.execute('INSERT INTO weather_data VALUES(?, ?, ?)',
                         (datetime.now().strftime('%d.%m.%Y %H:%m'), city, weather))
        await db.commit()


async def get_weather(city):
    await logger.info(f'Поступил запрос на получения погоды города {city}')
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'APPID': 'fc7ebccb3af53b048a7da5ad3e403215'}

    async with storage['session'].get(url=url, params=params) as response:
        if response.status == 200:
            data = await response.json()
            try:
                return data['weather'][0]['description']
            except (KeyError, json.JSONDecodeError) as err:
                print(f'Ошибка обработки данных погоды {err}')
                return 'Нет данных'
        else:
            print(f'Ошибка запроса погоды: Статус {response.status}')
            return 'Нет данных'


async def translate(text, source='ru', target='en'):
    await logger.info(f'Поступил запрос на перевод слова {text}')

    url = "https://api.mymemory.translated.net/get"

    params = {
        'q': text,
        'langpair': f'{source}|{target}'
    }

    async with storage['session'].get(url, params=params) as response:
        if response.status == 200:
            try:
                data = await response.json()
                translated_text = data['responseData']['translatedText']
                return translated_text
            except (KeyError, json.JSONDecodeError) as err:
                print(f'Ошибка обработки ответа перевода: {err}')
                return text
        else:
            print(f'Ошибка запроса перевода: Статус {response.status}')
            return text


async def handle(request):
    city_ru = request.rel_url.query.get('city')
    if not city_ru:
        return web.Response(text=json.dumps({'error': 'Не указан город'}), status=400, content_type='application/json')

    city_en = await translate(city_ru, 'ru', 'en')

    if city_en == city_ru:
        return web.Response(text=json.dumps({'error': 'Не удалось перевести название города'}), status=500, content_type='application/json')

    weather_en = await get_weather(city_en)
    weather_ru = await translate(weather_en, 'en', 'ru')

    await save_to_db(city_ru, weather_ru)

    result = {'Город': city_ru, 'Погода': weather_ru.capitalize()}
    return web.Response(text=json.dumps(result, ensure_ascii=False), content_type='application/json')


async def main():
    storage['session'] = ClientSession()

    async with storage['session']:
        await create_table()
        app = web.Application()

        app.add_routes([web.get('/weather', handle)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8000)
        await site.start()

        while True:
            await asyncio.sleep(10000)


if __name__ == '__main__':
    asyncio.run(main())
