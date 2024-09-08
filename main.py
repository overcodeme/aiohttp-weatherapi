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

            except KeyError:
                return 'Нет данных'

        else:
            print('Проверьте правильность введённых данных')


async def handle(request):
    city = request.rel_url.query['city']
    weather_data = await get_weather(city)
    result = {'city': city, 'weather': weather_data}

    return web.Response(text=json.dumps(result, ensure_ascii=False))


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

