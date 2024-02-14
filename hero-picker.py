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
from pathlib import Path


def get_hero_names(heroes):
    """Assigns a name string to each hero ID
    
    Args:
        heroes (json): Hero information obtained through queries.make_hero_info_query
    
    Returns:
        dict{int: str}: Dictionary of names for each hero ID
    """
    SHORTER_NAMES = {
        'Outworld Destroyer': 'Outworld D',
        'Ancient Apparition': 'Ancient A',
        'Vengeful Spirit': 'Vengeful S',
        'Centaur Warrunner': 'Centaur W',
        "Nature's Prophet": "Nature's P"
    }

    hero_names = {}
    for hero in heroes['constants']['heroes']:
        hero_names[hero['id']] = hero['displayName']
        if hero_names[hero['id']] in SHORTER_NAMES:
            hero_names[hero['id']] = SHORTER_NAMES[hero_names[hero['id']]]
    return hero_names


def get_hero_ids_from_names(config, heroes, hero_count):
    """Extracts the IDs of heroes for each position from the config file's include_heroes attribute.
    
    Args:
        config (json): Loaded user specific config file
        heroes (json): Hero information obtained through queries.make_hero_info_query
        hero_count (int): Number of meta heroes for each position
    
    Returns:
        list[list[int]]: List of hero IDs for each position
    """
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


def get_heroes(monitor_number, screenshot_path, roi_method, heroes):
    """Gets heroes from either a file image or screenshot.
    
    Args:
        monitor_number (int): Number of the monitor to get screenshot of (only used when screenshot_path is "live")
        screenshot_path (str): Either "live" to capture the screen or a path to the image to load from file
        roi_method (str): The method to detect ROIs, has to be either "predefined" or "contour"
        heroes (json): Hero information obtained through queries.make_hero_info_query
    
    Returns:
        tuple(list[int], list[int]): List of hero IDs for radiant and dire team
    """
    if screenshot_path != 'live':
        screenshot_path = str(Path(Path(__file__).parent, screenshot_path))
    images_path = Path(__file__).resolve().with_name('images')

    img = detection.make_screenshot(monitor_number, screenshot_path)
    rois = detection.predefined_rois() if roi_method == 'predefined' else detection.get_hero_rois(img)

    detected_heroes = detection.detect_heroes(heroes, img, rois, images_path)
    dire_heroes = [hero for hero in detected_heroes[:5] if hero]
    radiant_heroes = [hero for hero in detected_heroes[5:] if hero]
    return radiant_heroes, dire_heroes


def get_picks(config, is_radiant, heroes, meta_heroes, hero_names, hero_matchups, player_wrs, pos=None):
    """Displays the best heroes for the given team.
    
    Args:
        config (json): Loaded user specific config file
        is_radiant (bool): Determines if picking for radiant side
        heroes (json): Hero information obtained through queries.make_hero_info_query
        meta_heroes (list[list[tuple(int, float)]]): List of best heroes (their ID and win rate) for each position
        hero_names (dict{int: str}): Dictionary of hero names for hero indexes
        hero_matchups (dict{int: json}): Match up data for each hero ID (obtained through queries.make_heroes_matchup_query)
        player_wrs (json): Object containing player's win rates for each hero (obtained through queries.get_player_winrates function)
        pos (list[int], optional): List of positions to consider, by default includes all positions (1-5)
    """
    monitor_number = config['image']['monitor_number']
    screenshot_path = config['image']['screenshot']
    roi_method = config['image']['roi_method']

    radiant_heroes, dire_heroes = get_heroes(monitor_number, screenshot_path, roi_method, heroes)

    print('Detected radiant: ', [hero_names[hero] for hero in radiant_heroes])
    print('Detected dire: ', [hero_names[hero] for hero in dire_heroes])

    against_idx = dire_heroes if is_radiant else radiant_heroes
    with_idx = radiant_heroes if is_radiant else dire_heroes

    print("WITH: " + ', '.join([hero_names[hero] for hero in with_idx]))
    print("AGAINST: " + ', '.join([hero_names[hero] for hero in against_idx]))

    best_picks = stats.get_best_pick_by_pos(meta_heroes, hero_matchups, radiant_heroes, dire_heroes, is_radiant, pos)
    ui.print_best_picks(hero_names, best_picks, player_wrs)


async def get_hero_matchups(bracket, all_hero_count, stratz_token):
    """Gets the counters and synergy values for each hero
    
    Args:
        bracket (str): Selected bracket from the config
        all_hero_count (int): The number of all heroes
        stratz_token (TYPE): Player's Stratz API token
    
    Returns:
        dict{int: json}: Match up data for each hero ID
    """
    bracket_combined = bracket
    if bracket == 'IMMORTAL' or bracket == 'DIVINE':
        bracket_combined = 'DIVINE_IMMORTAL'
    hero_matchups = {}

    matchups = await queries.run_query(queries.make_heroes_matchup_query(bracket_combined, all_hero_count), stratz_token)
    for hero in matchups['heroStats']['matchUp']:
        hero_id = hero['heroId']
        hero_matchups[hero_id] = hero

    return hero_matchups


def show_grid(config, heroes, hero_names, hero_matchups):
    """Displays the tables of every hero counters and synergies for both teams.
    
    Args:
        config (json): Loaded user specific config file
        heroes (json): Hero information obtained through queries.make_hero_info_query
        hero_names (dict{int: str}): Dictionary of hero names for hero indexes
        hero_matchups (dict{int: json}): Match up data for each hero ID (obtained through queries.make_heroes_matchup_query)
    """
    stratz_token = config['stratz']['token']
    monitor_number = config['image']['monitor_number']
    screenshot_path = config['image']['screenshot']
    roi_method = config['image']['roi_method']
    bracket = config['stats']['bracket']

    radiant_heroes, dire_heroes = get_heroes(monitor_number, screenshot_path, roi_method, heroes)

    grid_vs, grid_rad, grid_dire = stats.calc_adv_matrix(radiant_heroes, dire_heroes, hero_matchups)
    ui.print_grids(radiant_heroes, dire_heroes, hero_names, grid_vs, grid_rad, grid_dire)


def cli(config, heroes, pos_heroes, hero_names, hero_matchups, player_wrs):
    """Runs the command-line interface loop that awaits user's input and executes the given command.
    
    Args:
        config (json): Loaded user specific config file
        heroes (json): Hero information obtained through queries.make_hero_info_query
        pos_heroes (list[list[tuple(int, float)]]): List of best heroes (their ID and win rate) for each position
        hero_names (dict{int: str}): Dictionary of hero names for hero indexes
        hero_matchups (dict{int: json}): Match up data for each hero ID (obtained through queries.make_heroes_matchup_query)
        player_wrs (json): Object containing player's win rates for each hero (obtained through queries.get_player_winrates function)
    """
    print('Type a command.')
    cmds = ['r (radiant)[pos]: analyze picks for radiant (optinally for given position, e.g. r2)',
        'd (dire)[pos]: analyze picks for dire (optinally for given position, e.g. d2)',
        't (test): test hero detection',
        'h (heroes): display hero details',
        'g (grid): detailed hero matchups',
        'q (quit): exit']
    for cmd in cmds:
        print(f'\t{cmd}')

    command = None
    while command != 'q':
        print('prompt> ', end='')
        command = input()
        picking = command.startswith('r') or command.startswith('d')
        if picking and (len(command) == 1 or len(command) == 2):
            pos = None
            if len(command) == 2:
                if command[1] not in set("12345"):
                    continue
                pos = [int(command[1])]
            is_radiant = command[0] == 'r'
            side = 'radiant' if is_radiant else 'dire'
            print(f'Picking for {side}')
            get_picks(config, is_radiant, heroes, pos_heroes, hero_names, hero_matchups, player_wrs, pos)
        elif command == 't':
            cfg_im = config['image']
            screenshot_path = cfg_im['screenshot']
            if screenshot_path != 'live':
                screenshot_path = str(Path(Path(__file__).parent, screenshot_path))
            detection.test_detection(cfg_im['monitor_number'], screenshot_path, cfg_im['roi_method'])
        elif command == 'h':
            ui.print_hero_data(heroes)
        elif command == 'g':
            show_grid(config, heroes, hero_names, hero_matchups)


async def get_player_winrates(player_id, all_hero_count, stratz_token):
    """Gets player's win rate for each hero.
    
    Args:
        player_id (long): Player's Steam ID from config
        all_hero_count (int): The number of all heroes
        stratz_token (str): Player's Stratz token
    
    Returns:
        dict{int: json}: A JSON object describing winrate for each hero ID
    """
    wrs = {}
    if player_id != None:
        data = await queries.run_query(queries.make_player_winrates_query(player_id, all_hero_count), stratz_token)
        for hero in data['player']['heroesPerformance']:
            wrs[hero['heroId']] = hero
    return wrs


async def main():
    # Load config and hero assets
    path_config = Path(__file__).resolve().with_name('config.json')
    with open(path_config, 'r', encoding='utf-8') as fp:
        config = json.load(fp)
    stratz_token = config['stratz']['token']
    monitor_number = config['image']['monitor_number']
    screenshot_path = config['image']['screenshot']
    hero_count = config['stats']['meta_heroes_count']
    pick_thr = config['stats']['pickrate_threshold']
    bracket = config['stats']['bracket']

    path_images = Path(__file__).resolve().with_name('images')
    assets.get_hero_assets(path_images)
    ui.init()

    # Get meta heroes for each role
    heroes = await queries.run_query(queries.make_hero_info_query(), stratz_token)
    hero_names = get_hero_names(heroes)
    all_hero_count = len(hero_names)

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

    matchups = await get_hero_matchups(bracket, all_hero_count, stratz_token)

    # Player's hero win rates
    player_wrs = await get_player_winrates(config['steam']['user'], all_hero_count, stratz_token)

    # Run CLI loop
    cli(config, heroes, pos_heroes, hero_names, matchups, player_wrs)


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
