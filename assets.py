import requests
import os
import urllib.request
from pathlib import Path


OPENDOTA_CDN = 'https://cdn.cloudflare.steamstatic.com'
OPENDOTA_API = 'https://api.opendota.com/api'


def get_hero_assets(folder):
    """Downloads the portraits of each hero to the given folder if it doesn't exist. The images are queried using OpenDota's API.
    
    Args:
        folder (str): Path to the hero images folder
    """
    if os.path.exists(folder):
        return
    os.makedirs(folder)

    resp = requests.get('/'.join([OPENDOTA_API, 'constants/heroes']))

    for hero_details in resp.json().values():
        img_uri = ''.join([OPENDOTA_CDN, hero_details['img']])
        print(f'{hero_details['id']} {hero_details['name']} {img_uri}')
        hero_name = hero_details['name'].removeprefix('npc_dota_hero_')
        file_name = Path(folder, hero_name + '.png')
        urllib.request.urlretrieve(img_uri, file_name)
