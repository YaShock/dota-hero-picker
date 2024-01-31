import asyncio
import json
import aiohttp
import sys

import queries
import ui
import assets
import stats
import detection
from misc import Error


def get_hero_names(heroes):
    SHORTER_NAMES = {
        'Outworld Destroyer': 'Outworld D',
        'Ancient Apparition': 'Ancient A',
        'Vengeful Spirit': 'Vengeful S',
        'Centaur Warrunner': 'Centaur W'
    }

    hero_names = {}
    for hero in heroes['constants']['heroes']:
        hero_names[hero['id']] = hero['displayName']
        if hero_names[hero['id']] in SHORTER_NAMES:
            hero_names[hero['id']] = SHORTER_NAMES[hero_names[hero['id']]]
    return hero_names


def get_hero_ids_from_names(config, heroes, hero_count):
    include_ids = [[], [], [], [], []]
    for pos in range(0, 5):
        incl = config['stats']['include_heroes'][f'pos_{pos + 1}']
        if len(incl) > hero_count:
            print(f'More heroes for pos {pos + 1} than selected meta hero count, skipping some')
        for hero_name in incl:
            # find id
            for hero_data in heroes['constants']['heroes']:
                if hero_data['shortName'] == hero_name:
                    include_ids[pos].append(hero_data['id'])
                    break
    return include_ids


def get_picks(config, is_radiant, heroes, pos_heroes, hero_names, meta_matchups):
    stratz_token = config['stratz']['token']
    monitor_number = config['image']['monitor_number']
    screenshot_path = config['image']['screenshot']
    roi_method = config['image']['roi_method']

    # Get screenshot
    img = detection.make_screenshot(monitor_number, screenshot_path)
    rois = detection.predefined_rois() if roi_method == 'predefined' else detection.get_hero_rois(img)

    detected_heroes = detection.detect_heroes(heroes, img, rois)
    dire_heroes = [hero for hero in detected_heroes[:5] if hero]
    radiant_heroes = [hero for hero in detected_heroes[5:] if hero]            

    print('Detected radiant: ', [hero_names[hero] for hero in radiant_heroes])
    print('Detected dire: ', [hero_names[hero] for hero in dire_heroes])

    best_picks = stats.get_best_pick_by_pos(pos_heroes, hero_names, meta_matchups, radiant_heroes, dire_heroes, stratz_token, is_radiant)
    ui.print_best_picks(hero_names, best_picks)


def cli(config, heroes, pos_heroes, hero_names, meta_matchups):
    print('Type r (radiant), d (dire) to analyze picks, t (test) to test detection, h (heroes) to display hero details, or q (quit) to exist.')
    command = None
    while command != 'q':
        print('prompt> ', end='')
        command = input()
        if command == 'r' or command == 'd':
            is_radiant = command == 'r'
            side = 'radiant' if is_radiant else 'dire'
            print(f'Picking for {side}')
            get_picks(config, is_radiant, heroes, pos_heroes, hero_names, meta_matchups)
        elif command == 't':
            cfg_im = config['image']
            detection.test_detection(cfg_im['monitor_number'], cfg_im['screenshot'], cfg_im['roi_method'])
        elif command == 'h':
            ui.print_hero_data(heroes)


async def main():
    # Load config and hero assets
    with open('config.json', 'r', encoding='utf-8') as fp:
        config = json.load(fp)
    stratz_token = config['stratz']['token']
    monitor_number = config['image']['monitor_number']
    screenshot_path = config['image']['screenshot']
    hero_count = config['stats']['meta_heroes_count']
    pick_thr = config['stats']['pickrate_threshold']
    bracket = config['stats']['bracket']

    assets.get_hero_assets('images')

    # Get meta heroes for each role
    heroes = await queries.run_query(queries.make_hero_info_query(), stratz_token)
    hero_names = get_hero_names(heroes)

    pos_win_rates = []
    for pos in range(0, 5):
        win_rates = await queries.run_query(queries.make_hero_winrate_query(pos + 1, bracket), stratz_token)
        pos_win_rates.append(win_rates)

    pos_heroes = stats.get_best_heroes_by_pos(pos_win_rates, pick_thr, hero_count)
    print('Meta picks')
    ui.print_meta_heroes(pos_heroes, hero_names, hero_count)

    # Replace worst meta picks with custom picks
    include_ids = get_hero_ids_from_names(config, heroes, hero_count)
    pos_heroes = stats.include_heroes(pos_heroes, include_ids, hero_count, pos_win_rates)
    print()
    print('Meta + custom picks')
    ui.print_meta_heroes(pos_heroes, hero_names, hero_count)

    print('Getting matchups for each meta hero')
    all_meta_heroes = set()
    for pos in range(0, 5):
        for hero in pos_heroes[pos]:
            all_meta_heroes.add(hero[0])

    bracket_combined = bracket
    if bracket == 'IMMORTAL' or bracket == 'DIVINE':
        bracket_combined = 'DIVINE_IMMORTAL'
    meta_matchups = {}
    for hero in all_meta_heroes:
        matchups = await queries.run_query(queries.make_hero_matchup_query(hero, bracket_combined), stratz_token)
        meta_matchups[hero] = matchups

    # Run CLI loop
    cli(config, heroes, pos_heroes, hero_names, meta_matchups)


if __name__ == '__main__':
    coro = main()
    try:
        asyncio.run(coro)
    except aiohttp.ClientError:
        raise Error('Something happened with the network. Maybe Stratz is unavailable or your internet is down.')
    except Error as e:
        print('Error: {}\n'.format(e.args[0]))
    finally:
        if getattr(sys, "frozen", False):
            input()
