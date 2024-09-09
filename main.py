from aiohttp import ClientSession, web
import asyncio
import json

storage = {}


async def get_weather(city):
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'APPID': 'fc7ebccb3af53b048a7da5ad3e403215'}

    async with storage['session'].get(url=url, params=params) as response:
        if response.status == 200:
            data = await response.json()
            try:
                return data['weather'][0]['main']
            except (KeyError, json.JSONDecodeError) as err:
                print(f'Ошибка обработки данных погоды {err}')
                return 'Нет данных'
        else:
            print(f'Ошибка запроса погоды: Статус {response.status}')
            return 'Нет данных'


async def translate(text, source='auto', target='en'):
    url = 'https://ru.libretranslate.com/translate'
    data = {
        'q': text,
        'source': source,
        'target': target,
        'format': 'text',
        'alternatives': 3,
        'api_key': ''  # Оставьте пустым, если не требуется ключ API
    }
    headers = {
        'Content-Type': 'application/json'
    }

    async with storage['session'].post(url, json=data, headers=headers) as response:
        if response.status == 200:
            response_json = await response.json()
            try:
                return response_json['translatedText']
            except KeyError:
                print('Ошибка обработки ответа перевода')
                return text
        else:
            print(f'Ошибка запроса перевода: Статус {response.status}')
            return text


async def handle(request):
    city_ru = request.rel_url.query['city']
    if not city_ru:
        return web.Response(text=json.dumps({'error': 'Не указан город'}), status=400, content_type='application/json')

    city_en = await translate(city_ru, 'ru', 'en')
    if city_en == city_ru:
        return web.Response(text=json.dumps({'error': 'Не удалось перевести название города'}), status=500, content_type='application/json')

    weather_en = await get_weather(city_en)
    weather_ru = await translate(weather_en, 'en', 'ru')

    result = {'Город': city_ru, 'Погода': weather_ru}
    return web.Response(text=json.dumps(result, ensure_ascii=False), content_type='application/json')


async def main():
    storage['session'] = ClientSession()

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