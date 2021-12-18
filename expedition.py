import re
import time
import json
import random
import requests
from bs4 import BeautifulSoup

from ogame import OGame

def console(text):
    print(f"[{time.strftime('%d-%m-%Y %H:%M:%S')}] " + str(text))


def available_exp():
    r = ogame.s.get(f'https://s{ogame.server}-{ogame.language}.ogame.gameforge.com/game/index.php',
        params={'page': 'ingame', 'component': 'fleetdispatch'}).text
    fleets = int(re.search('var fleetCount = (.*);', r).group(1))
    max_fleets = int(re.search('var maxFleetCount = (.*);', r).group(1))
    exps = int(re.search('var expeditionCount = (.*);', r).group(1))
    max_exps = int(re.search('var maxExpeditionCount = (.*);', r).group(1))
    console(f'Fleets: {fleets}/{max_fleets} | Exp: {exps}/{max_exps}')

    # ships_on_planet = json.loads(re.search('var shipsOnPlanet = (.*);', r).group(1))
    # token = re.search('var token = "(.*)";', r).group(1)

    # for ship in ships_on_planet:
    #     ship_id = ship['id']
    #     if ship['number'] < ships[ship_id]:
    #         console(f'no ships {ship_id}')
    #         return 0

    available_exp = min(max_exps - exps, max_fleets - fleets)
    console(f'Available expeditions: {available_exp}')
    return available_exp


def expedition():
    if int(time.time()) >= ogame.exp_return_time:
        if not ogame.check_logged_in():
            ogame.login_token(auth_token, server=176, language='ru')

        while available_exp() != 0:
            res = ogame.send_exp(origin=ogame.planet('4:200:15'), target=ogame.planet('4:200:16'), ships=exp_ships)
            if res['success']:
                console(f'Expedition sended')
            else:
                console(f'Send error: {res["message"]}')
            time.sleep(1)
            
        ogame.exp_return_time = ogame.get_exp_return_time()
        human_time = time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(ogame.exp_return_time))
        console(f'Next return time: {human_time}')


ogame = OGame()
auth_token = 'your_token_here'
exp_ships = {
    'am207': 30, # Линкор
    'am213': 1, # Уничтожитель
    'am219': 1, # Первопроходец
    'am202': 40, # Малый транспорт
    'am203': 150, # Большой транспорт
    'am209': 1, # Переработчик
    'am210': 1 # Шпионский зонд
}

ogame.login_token(auth_token, server=176, language='ru')
ogame.load_planets()

while True:
    try:
        expedition()
    except Exception as e:
        console(f'{e}')
    time.sleep(5)