from colorama import init as colorama_init
from colorama import Fore, Style


def init():
    colorama_init(autoreset=True)


def print_grid(radiant_heroes, dire_heroes, adv_matrix):
    r_heroes = [hero['name'].removeprefix('npc_dota_hero_') for hero in radiant_heroes]
    d_heroes = [hero['name'].removeprefix('npc_dota_hero_') for hero in dire_heroes]
    long_rad_hero = max(r_heroes, key=len)
    header = ' ' * len(long_rad_hero) + ' '.join(d_heroes)
    print(header)
    for row, r_hero in enumerate(r_heroes):
        print(r_hero, end='')
        extra_pad = len(long_rad_hero) - len(r_hero)
        print(' ' * extra_pad, end='')
        for col, d_hero in enumerate(d_heroes):
            val = adv_matrix[row][col]
            val_str = str(round(val, 2)) + '%'
            s_len = len(val_str)
            pad_left = (len(d_hero) - s_len) // 2
            pad_right = len(d_hero) - pad_left - s_len - 2
            print(' ' * pad_left, val_str, ' ' * pad_right, end='')
        print()


def print_meta_heroes(meta_pos, hero_names, hero_count=10):
    longest_name = max(hero_names.values(), key=len)
    col_width = len(longest_name) + 5

    # Print header
    for i in range(0, 5):
        s = f'Position {i + 1} '
        pad = col_width - len(s)
        s += ' ' * pad
        print(s, end='')
    print()

    for i in range(0, hero_count):
        for pos in range(0, 5):
            hero = meta_pos[pos][i][0]
            hero_name = hero_names[hero]
            val = meta_pos[pos][i][1]
            val_str = str(round(val * 100, 2)) + '%'
            out = f'{hero_name}: {val_str} '
            pad = col_width - len(out)
            out += ' ' * pad
            print(out, end='')
        print()


def print_best_picks(hero_names, best_by_pos, player_wrs):
    column_lengths = [0, len('counter'), len('synergy'), len('value'), len('player')]
    longest_name = max(hero_names.values(), key=len)
    column_lengths[0] = len(longest_name)
    print(' ' * column_lengths[0] + ' COUNTER' + ' SYNERGY' + ' VALUE' + ' PLAYER')


    def colorize(s):
        color = Fore.GREEN if float(s) > 0 else Fore.RED
        return color + s

    def colorize_percent(s, val):
        color = Fore.GREEN if val >= 0.5 else Fore.RED
        return color + s

    for pos in range(0, 5):
        print(f'POSITION {pos+1}:')
        best = best_by_pos[pos]
        for hero_id, counter, synergy, val in best:
            name = hero_names[hero_id]
            cntr_str = str(round(counter, 2))
            syn_str = str(round(synergy, 2))
            val_str = str(round(val, 2))
            wr_str = 'No data'
            cntr_str_clr = colorize(cntr_str)
            syn_str_clr = colorize(syn_str)
            val_str_clr = colorize(val_str)
            wr_str_clr = Style.RESET_ALL + 'No data'
            if hero_id in player_wrs:
                wins = player_wrs[hero_id]['winCount']
                matches = player_wrs[hero_id]['matchCount']
                wr = wins / matches
                wr_str = str(round(wr * 100, 2)) + '%'
                wr_str_clr = colorize_percent(wr_str.ljust(6), wr)
                wr_str_clr += f' ({wins}/{matches})'
            s = name
            s += ' ' * (column_lengths[0] - len(name) + 1)
            s += cntr_str_clr
            s += ' ' * (column_lengths[1] - len(cntr_str) + 1)
            s += syn_str_clr
            s += ' ' * (column_lengths[2] - len(syn_str) + 1)
            s += val_str_clr
            s += ' ' * (column_lengths[3] - len(val_str) + 1)
            s += wr_str_clr
            s += ' ' * (column_lengths[4] - len(wr_str))
            print(s)


def print_hero_data(heroes):
    import json
    formatted = json.dumps(heroes, indent=2)
    print(formatted)
