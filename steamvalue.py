from __future__ import division
import os
import requests
from flask import (Flask, jsonify, request, render_template,
                   redirect, url_for, flash)
from flask_caching import Cache

import newrelic.agent
newrelic.agent.initialize()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'some_secret_idontcare')
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

api_key = os.environ.get('API_KEY')
if not api_key:
    raise Exception("Invalid API Key")

class Steam:
    def __init__(self, api_key):
        self.api_key = api_key
        self.api = requests.session()

    @cache.memoize()
    def get_steam_id(self, name):
        'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/'
        '?key=xxx&vanityurl=userVanityUrlName'
        params = {
            'key': self.api_key,
            'vanityurl': name,
        }
        return self.api.get('http://api.steampowered.com/'
                            'ISteamUser/ResolveVanityURL/v0001/',
                            params=params).json()

    @cache.memoize()
    def get_user_games(self, steam_id):
        'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
        '?key=xxxx&steamid=xxxxxxx&format=json&include_appinfo=1'
        params = {
            'key': self.api_key,
            'steamid': steam_id,
            'include_appinfo': 1
        }
        return self.api.get('http://api.steampowered.com/'
                            'IPlayerService/GetOwnedGames/v0001/',
                            params=params).json()

    @cache.memoize()
    def get_game_price(self, app_id):
        'http://store.steampowered.com/api/appdetails?appids=57690'
        params = {
            'appids': app_id,
            'filters': 'price_overview'
        }
        return self.api.get('http://store.steampowered.com/'
                            'api/appdetails', params=params).json()


@app.errorhandler(404)
def error_404(e):
    return redirect(url_for('index'))


@app.errorhandler(500)
def error(e):
    return """"Shit sorry mate, looks like you cause an error...
        Go back and try again?"""


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/games/<name>')
@cache.memoize(60)
def by_name(name):
    api = Steam(api_key)

    try:
        steam_id = api.get_steam_id(name)['response']['steamid']
    except:
        steam_id = name
    try:
        games = api.get_user_games(steam_id)['response']['games']
    except:
        flash("Unable to find that user")
        return redirect(url_for('index'))
    games = sorted(games, key=lambda k: k['playtime_forever'], reverse=True)

    most_played = request.args.get('most_played', 50)
    limit = int(request.args.get('limit', 10))

    top_list = []
    for game in games[:most_played]:
        try:
            price = api.get_game_price(game['appid'])
            app_id = str(game['appid'])
            price = price[app_id]['data']['price_overview']
        except:
            print("invalid price for", game['appid'])
            continue
        cost = price['initial'] / 100
        hours = round(game['playtime_forever'] / 60, 2)
        try:
            value = round(cost / hours, 2)
        except ZeroDivisionError:
            value = cost
        if hours < 1:
            value = cost
        top_list.append({'name': game['name'], 'appid': game['appid'],
                         'cost': cost, 'cost_per_hour': value,
                         'playtime': hours})
    top_list = sorted(top_list, key=lambda k: k['cost_per_hour'])

    if request.args.get('format') == 'json':
        return jsonify(games=top_list[:limit])

    return render_template('games.html',
                           steam_name=name, games=top_list[:limit])


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
