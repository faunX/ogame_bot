import re
import time
import json
import random
import requests
from bs4 import BeautifulSoup

from ogame import OGame

def console(text):
    print(f"[{time.strftime('%d-%m-%Y %H:%M:%S')}] " + str(text))


def check_ships(ships_on_planet):
    on_planet_dict = {}
    for ship in ships_on_planet:
        on_planet_dict.update({int(ship['id']): int(ship['number'])})

    for ship_id, ship_count in list(exp_ships.items()):
        # Если вообще нет кораблей
        if int(ship_id[2:]) not in on_planet_dict:
            console(f'Send error: no ships {ship_id}')
            return False
        else:
            # Если есть, но меньше, чем надо
            if on_planet_dict[int(ship_id[2:])] < ship_count:
                console(f'Send error: need more ships {ship_id}')
                return False
    return True


def available_exp(origin):
    r = ogame.s.get(f'https://s{ogame.server}-{ogame.language}.ogame.gameforge.com/game/index.php',
        params={'page': 'ingame', 'component': 'fleetdispatch', 'cp': origin.id}).text
    fleets = int(re.search('var fleetCount = (.*);', r).group(1))
    max_fleets = int(re.search('var maxFleetCount = (.*);', r).group(1))
    exps = int(re.search('var expeditionCount = (.*);', r).group(1))
    max_exps = int(re.search('var maxExpeditionCount = (.*);', r).group(1))

    # Когда заканиваются доп слоты и флотов больше, чем может быть
    available_fleets = max(0, max_fleets - fleets)
    available_exp = max(0, max_exps - exps)

    # Экспедиции доступны, только если есть слоты под флоты
    available_exp = min(available_exp, available_fleets)
    console(f'Fleets: {fleets}/{max_fleets} | Exp: {exps}/{max_exps} | Available exp: {available_exp}')

    # Проверяем корабли, только если есть слот под экспедицию
    if available_exp > 0:
        ships_on_planet = json.loads(re.search('var shipsOnPlanet = (.*);', r).group(1))
        if not check_ships(ships_on_planet):
            # Если проблема с кораблями, то следующая проверка через 10 мин
            ogame.exp_check_time = int(time.time()) + 600
            return 0

    return available_exp


def expedition(origin, target):
    if int(time.time()) >= ogame.exp_return_time:
        if not ogame.check_logged_in():
            ogame.login_token(auth_token, server=176, language='ru')

        # Время проверки из-за ошибки устанавливаем максимально большое
        ogame.exp_check_time = float('inf')

        while available_exp(origin) != 0:
            res = ogame.send_exp(origin, target, exp_ships)
            if res['success']:
                console(f'Expedition sended')
            else:
                console(f'Send error: {res["message"]}')
                return_time = ogame.get_exp_return_time()
                ogame.exp_check_time = int(time.time()) + 600
                ogame.exp_return_time = min(return_time, ogame.exp_check_time)
                break
            time.sleep(5)
        else:
            # Минимальное время из проверки по ошибке и следующего возвращения
            ogame.exp_return_time = min(ogame.exp_check_time, ogame.get_exp_return_time())

        human_time = time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(ogame.exp_return_time))
        console(f'Next checking time: {human_time}')


ogame = OGame()
auth_token = 'your_token_here'
exp_ships = {
    'Большой транспорт': 150,
    'Линкор': 30,
    'Первопроходец': 5,
    'Шпионский зонд': 3,
    'Уничтожитель': 3,
}

ogame.login_token(auth_token, server=176, language='ru')
ogame.load_planets()

origin = ogame.moon('4:200:15')
target = ogame.planet('4:200:16')

while True:
    try:
        expedition(origin, target)
    except Exception as e:
        console(f'{e}')
    time.sleep(5)