import re
import time
import json
import random
import requests
from bs4 import BeautifulSoup


class Planet:
    def __init__(self, id, type, coords, name):
        self.id = id
        self.type = type
        self.coords = coords
        self.name = name

    def __repr__(self):
        return f'<Planet id={self.id}, type={self.type}, coords={self.coords}, name={self.name}>'


class Fleet:
    def __init__(self, game):
        self.game = game
        self.s = game.s
        self.target = None
        self.ships = None
        self.mission = None
        self.speed = 10
        self.token = None
        self.origin = None
        self.resources = [0,0,0]
        self.holding_time = 1

    def send(self):
        if self.target is None:
            return {'success': False, 'message': 'Не указаны координаты назначения'}

        if self.ships is None:
            return {'success': False, 'message': 'Не выбраны корабли'}
        else:
            self.ships = self.game.convert_ships(self.ships)

        if self.mission is None:
            return {'success': False, 'message': 'Не выбрана миссия'}

        if self.origin is None:
            return {'success': False, 'message': 'Не выбрана планета вылета'}

        if self.token is None:
            r = self.s.get(f'https://s{self.game.server}-{self.game.language}.ogame.gameforge.com/game/index.php',
                params={'page': 'ingame', 'component': 'fleetdispatch'}
            )
            self.token = re.search('var token = "(.*)";', r.text).group(1)

        target = self.target.coords.split(':')

        data = {
            "token": self.token,
            "galaxy": target[0],
            "system": target[1],
            "position": target[2],
            "type": self.target.type,
            "metal": self.resources[0],
            "crystal": self.resources[1],
            "deuterium": self.resources[2],
            "mission": self.mission,
            "speed": self.speed,
            "union": "0",
        }
        data.update(self.ships)

        # если экспедиция, то ставим возврат и время
        if self.mission in [15]:
            data.update({"retreatAfterDefenderRetreat": "0"})
            data.update({"holdingtime": "1"})

        r = self.s.post(f'https://s{self.game.server}-{self.game.language}.ogame.gameforge.com/game/index.php',
            params={
                'page': 'ingame',
                'component': 'fleetdispatch',
                'action': 'sendFleet',
                'ajax': '1',
                'asJson': '1',
                'cp': self.origin.id,
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
            },
            data=data
        )

        res = r.json()
        if res['success']:
            return {'success': True, 'message': res['message']}
        else:
            return {'success': False, 'message': res['errors'][0]['message']} 


class OGame:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'})
        self.server = None
        self.language = None
        self.planets = []
        self.exp_return_time = 0
        self.exp_check_time = float('inf')
        self.exp_coord_counter = 0

    def planet(self, coords):
        for planet in self.planets:
            if (planet.coords == coords or planet.name == coords) and planet.type == 1:
                return planet
        return Planet(None, 1, coords, f'Planet {coords}')

    def moon(self, coords):
        for planet in self.planets:
            if (planet.coords == coords or planet.name == coords) and planet.type == 3:
                return planet
        return Planet(None, 3, coords, f'Moon {coords}')

    def field(self, coords):
        return Planet(None, 2, coords, 'Поле обломков')

    def login(self, username, password, server, language):
        self.username = username
        self.password = password
        self.server = server
        self.language = language

        r = self.s.post('https://gameforge.com/api/v1/auth/thin/sessions',
            data=json.dumps({
                "autoGameAccountCreation": False,
                "gameEnvironmentId": "0a31d605-ffaf-43e7-aa02-d06df7116fc8",
                "gfLang": "ru",
                "identity": self.username,
                "locale": "ru_RU",
                "password": self.password,
                "platformGameId": "1dfd8e7e-6e1a-4eb1-8c64-03c3b62efd2f"
            }),
            headers={
                'Content-Type': 'application/json'
            }
        )
        token = r.json()['token']

        r = self.s.get('https://lobby.ogame.gameforge.com/api/users/me/accounts',
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}',
            }
        )

        account = None
        for account in r.json():
            if account['server']['number'] == server:
                break
        if account is None:
            return False

        r = self.s.get('https://lobby.ogame.gameforge.com/api/users/me/loginLink',
            params={
                "id": account['id'],
                "server[language]": account['server']['language'],
                "server[number]": account['server']['number'],
                "clickedButton": "quick_join"
            },
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}',
            }
        )
        auth_url = r.json()['url'].replace('\\', '')
        self.s.get(auth_url)

        if not self.check_logged_in():
            return False

        self.load_planets()
        return True


    def login_token(self, token, server, language):
        self.server = server
        self.language = language

        r = self.s.get('https://lobby.ogame.gameforge.com/api/users/me/accounts',
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}',
            }
        )

        account = None
        for account in r.json():
            if account['server']['number'] == server:
                break
        if account is None:
            return False

        r = self.s.get('https://lobby.ogame.gameforge.com/api/users/me/loginLink',
            params={
                "id": account['id'],
                "server[language]": account['server']['language'],
                "server[number]": account['server']['number'],
                "clickedButton": "quick_join"
            },
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}',
            }
        )
        auth_url = r.json()['url'].replace('\\', '')
        self.s.get(auth_url)

        if not self.check_logged_in():
            return False

        self.load_planets()
        return True


    def check_logged_in(self):
        r = self.s.get(f'https://s{self.server}-{self.language}.ogame.gameforge.com/game/index.php',
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
            params={
                'page': 'componentOnly',
                'component': 'eventList',
                'action': 'fetchEventBox',
                'ajax': '1',
                'asJson': '1',
            }
        )

        try:
            r = r.json()
        except json.decoder.JSONDecodeError:
            return False
        return True


    def load_planets(self):
        r = self.s.get(f'https://s{self.server}-{self.language}.ogame.gameforge.com/game/index.php',
            params={
                'page': 'ingame',
                'component': 'overview',
            }
        )
        soup = BeautifulSoup(r.text, 'lxml')
        planets = soup.select('#planetList div')
        for planet in planets:
            planet_id = int(planet['id'].split('-')[1])
            planet_coords = planet.select_one('.planet-koords').text.replace('[', '').replace(']', '')
            planet_name = planet.select_one('a.planetlink')['title'].split('[')[0].replace('<b>', '').strip()
            self.planets.append(Planet(planet_id, 1, planet_coords, planet_name))
        
            moon = planet.select_one('a.moonlink')
            if moon is not None:
                moon_id = moon['href'].split('cp=')[1]
                moon_name = moon['title'].split('[')[0].replace('<b>', '').strip()
                self.planets.append(Planet(moon_id, 3, planet_coords, moon_name))


    def get_events(self):
        r = self.s.get(f'https://s{self.server}-{self.language}.ogame.gameforge.com/game/index.php',
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
            params={
                'page': 'componentOnly',
                'component': 'eventList',
                'action': 'fetchEventBox',
                'ajax': '1',
                'asJson': '1',
            }
        )
        return r.json()


    def get_exp_return_time(self):
        r = self.s.get(f'https://s{self.server}-{self.language}.ogame.gameforge.com/game/index.php',
            params={
                'page': 'componentOnly',
                'component': 'eventList',
                'ajax': '1',
            }
        )
        # print(r.text)
        soup = BeautifulSoup(r.text, 'lxml')
        fleets = soup.select('tr.eventFleet')
        for fleet in fleets:
            if int(fleet['data-mission-type']) == 15 and fleet['data-return-flight'] == 'true':
                return int(fleet['data-arrival-time'])
        return int(time.time())+600


    def send_res(self, origin, target):
        r = self.s.get(f'https://s{self.server}-{self.language}.ogame.gameforge.com/game/index.php',
            params={'page': 'ingame', 'component': 'fleetdispatch', 'cp': origin.id}
        ).text

        # fleet_count = int(re.search('var fleetCount = (.*);', r).group(1))
        # max_fleet_count = int(re.search('var maxFleetCount = (.*);', r).group(1))

        res_m = int(re.search('var metalOnPlanet = (.*);', r).group(1))
        res_c = int(re.search('var crystalOnPlanet = (.*);', r).group(1))
        res_d = int(re.search('var deuteriumOnPlanet = (.*);', r).group(1))

        ships_on_planet = json.loads(re.search('var shipsOnPlanet = (.*);', r).group(1))

        token = re.search('var token = "(.*)";', r).group(1)

        ship_id = 203
        ship_count = 0
        ship_capacity = 0

        for ship in ships_on_planet:
            if ship['id'] == ship_id:
                ship_count = ship['number']
                ship_capacity = ship['cargoCapacity']

        if ship_capacity >= res_m + res_c + res_d:
            resources = [res_m, res_c, res_d]
        elif ship_capacity >= res_c + res_d:
            resources = [ship_capacity-res_c-res_d, res_c, res_d]
        elif ship_capacity >= res_d:
            resources = [0, ship_capacity-res_d, res_d]
        else:
            resources = [0, 0, res_d-ship_capacity]

        print(origin.coords, resources)

        fleet = Fleet(self)
        fleet.origin = origin
        fleet.target = target
        fleet.mission = 3
        fleet.ships = {'Большой транспорт': ship_count}
        fleet.resources = resources
        res = fleet.send()
        print(res)


    def send_exp(self, origin, target, ships):
        fleet = Fleet(self)
        fleet.origin = origin
        fleet.target = target
        fleet.mission = 15
        fleet.ships = ships
        res = fleet.send()
        return res


    def convert_ships(self, ships):
        rename_key(ships, 'Лёгкий истребитель', 'am204')
        rename_key(ships, 'Тяжёлый истребитель', 'am205')
        rename_key(ships, 'Крейсер', 'am206')
        rename_key(ships, 'Линкор', 'am207')
        rename_key(ships, 'Линейный крейсер', 'am215')
        rename_key(ships, 'Бомбардировщик', 'am211')
        rename_key(ships, 'Уничтожитель', 'am213')
        rename_key(ships, 'Звезда смерти', 'am214')
        rename_key(ships, 'Жнец', 'am218')
        rename_key(ships, 'Первопроходец', 'am219')
        rename_key(ships, 'Малый транспорт', 'am202')
        rename_key(ships, 'Большой транспорт', 'am203')
        rename_key(ships, 'Колонизатор', 'am208')
        rename_key(ships, 'Переработчик', 'am209')
        rename_key(ships, 'Шпионский зонд', 'am210')
        return ships
    

def rename_key(dictionary, old_name, new_name):
    try:
        dictionary[new_name] = dictionary.pop(old_name)
    except KeyError:
        pass


if __name__ == '__main__':
    # Создание экземпляра класса игры
    ogame = OGame()

    # Авторизация через логин и пароль
    # ogame.login('username', 'password', server=176, language='ru')

    # Авторизация через токен
    # ogame.login_token('xxxxxxxxxxxxxxxxxxx', server=176, language='ru')

    # Авторизация через куки
    # ogame.server = 176
    # ogame.language = 'ru'
    # ogame.s.cookies.set('maximizeId', 'null')
    # ogame.s.cookies.set('pc_idt', 'qqqqqqq')
    # ogame.s.cookies.set('PHPSESSID', 'wwwwwww')
    # ogame.s.cookies.set('prsess_xxxxxx', 'eeeeeee')

    # Проверка авторизации
    # ogame.check_logged_in()

    # Параметры origin и target:
    # print(ogame.planet('4:200:15')) # Планета по координатам
    # print(ogame.planet('Главная планета')) # Планета по названию
    # print(ogame.moon('4:200:15')) # Луна
    # print(ogame.field('4:200:15')) # Поле обломков

    # Пересылка всех ресурсов на главную планету
    # ogame.send_res(origin=ogame.planet('4:200:8'), target=ogame.planet('4:200:15'))
    # ogame.send_res(origin=ogame.planet('4:200:9'), target=ogame.planet('4:200:15'))
    # ogame.send_res(origin=ogame.planet('4:200:10'), target=ogame.planet('4:200:15'))
    # ogame.send_res(origin=ogame.planet('4:200:11'), target=ogame.planet('4:200:15'))
    # ogame.send_res(origin=ogame.planet('4:200:12'), target=ogame.planet('4:200:15'))
    # ogame.send_res(origin=ogame.planet('4:200:13'), target=ogame.planet('4:200:15'))

    # Можно отправлять флоты так
    # fleet = Fleet(ogame)
    # fleet.origin = ogame.planet('4:200:15')
    # fleet.target = ogame.planet('4:200:11')
    # fleet.mission = 3
    # fleet.ships = {'Большой транспорт': 38}
    # fleet.resources = [928000, 464000, 0]
    # res = fleet.send()
    # print(res['message'])

    # Список кораблей для экспедиции
    # exp_ships = {
    #     'Линкор': 30,
    #     'Уничтожитель': 1,
    #     'Первопроходец': 1,
    #     'Малый транспорт': 40,
    #     'Большой транспорт': 150,
    #     'Переработчик': 1,
    #     'Шпионский зонд': 1,
    # }

    # Отправка экспедиции
    # ogame.send_exp(origin=ogame.planet('4:200:15'), target=ogame.planet('4:200:16'), ships=exp_ships)

    # Полный список кораблей
    # ships = {
    #     'Лёгкий истребитель': 0, # fighterLight
    #     'Тяжёлый истребитель': 0, # fighterHeavy
    #     'Крейсер': 0, # cruiser
    #     'Линкор': 0, # battleship
    #     'Линейный крейсер': 0, # interceptor
    #     'Бомбардировщик': 0, # bomber
    #     'Уничтожитель': 0, # destroyer
    #     'Звезда смерти': 0, # deathstar
    #     'Жнец': 0, # reaper
    #     'Первопроходец': 0, # explorer
    #     'Малый транспорт': 0, # transporterSmall
    #     'Большой транспорт': 0, # transporterLarge
    #     'Колонизатор': 0, # colonyShip
    #     'Переработчик': 0, # recycler
    #     'Шпионский зонд': 0, # espionageProbe
    # }