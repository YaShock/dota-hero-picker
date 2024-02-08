from colorama import init as colorama_init
from colorama import Fore, Style


def init():
    """Initiates colorama for the colorful console printing.
    """
    colorama_init(autoreset=True)


def print_table(data, header_row=None, header_col=None, min_col_width=0, data_format=None, row_first=True, header_col_len=0):
    """Print 2D data in a table format, optionally with row and column headers.
    
    Args:
        data (list[list[Any]]): The 2D data to be printed
        header_row (list[str], optional): Horizontal header
        header_col (list[str], optional): Vertical header
        min_col_width (int, optional): Minimum number of characters for each column (using spaces for padding)
        data_format (function, optional): A function(str) -> str that formats each entry for output
        row_first (bool, optional): Donates if data is structured in row-first format
        header_col_len (int, optional): Pads the first (header) column to the given length if set to non 0
    """
    if header_row:
        header = ' '.join([e.ljust(min_col_width) for e in header_row])
        if header_col:
            if header_col_len == 0:
                header_col_len = len(max(header_col, key=len))
            header = header.rjust(len(header) + header_col_len + 1)
        print(header)

    range1 = range(len(data)) if row_first else range(len(data[0]))
    range2 = range(len(data[0])) if row_first else range(len(data))

    for idx1 in range1:
        if header_col:
            print(header_col[idx1].ljust(header_col_len + 1), end='')

        for idx2 in range2:
            val = data[idx1][idx2] if row_first else data[idx2][idx1]
            if data_format:
                val = data_format(val)
            val = str(val).ljust(min_col_width + 1)
            if header_row:
                val = val.ljust(len(header_row[idx2]) + 1)
            print(val, end='')
        print()


def print_grids(radiant_heroes, dire_heroes, hero_names, mat_vs, mat_with_rad, mat_with_dire):
    """Prints the tables of every hero counters and synergies for both teams.
    
    Args:
        radiant_heroes (list[int]): List of hero indexes for radiant
        dire_heroes (list[int]): List of hero indexes for dire
        hero_names (dict{int: str}): Dictionary of hero names for hero indexes
        mat_vs (list[list[float]]): 2D list of counter value of each radiant hero against each dire hero
        mat_with_rad (list[list[float]]): 2D list of synergy value of each radiant hero with other radiant heroes
        mat_with_dire (list[list[float]]): 2D list of synergy value of each dire hero with other dire heroes
    """
    r_heroes = [hero_names[hero] for hero in radiant_heroes]
    d_heroes = [hero_names[hero] for hero in dire_heroes]

    def entry_format(val):
        return str(round(val, 2)) + '%'

    print('Counters')
    print_table(mat_vs, d_heroes, r_heroes, min_col_width=6, data_format=entry_format)
    print('Synergy Radiant')
    print_table(mat_with_rad, r_heroes, r_heroes, min_col_width=6, data_format=entry_format)
    print('Synergy Dire')
    print_table(mat_with_dire, d_heroes, d_heroes, min_col_width=6, data_format=entry_format)


def print_meta_heroes(meta_pos, hero_names, hero_count=10):
    """Prints best meta heroes and their win rates for each position.
    
    Args:
        meta_pos (list[list[tuple(int, float)]]): List of heroes for each position containing their ID and win rate
        hero_names (dict{int: str}): Dictionary of hero names for hero indexes
        hero_count (int, optional): The number of meta heroes to be printed for each position
    """
    longest_name = max(hero_names.values(), key=len)
    col_width = len(longest_name) + 5

    def entry_format(entry):
        hero = entry[0]
        hero_name = hero_names[hero]
        val = entry[1]
        val_str = str(round(val * 100, 2)) + '%'
        return f'{hero_name}: {val_str}'

    header = [f'Position {i + 1}' for i in range(0, 5)]
    print_table(meta_pos, header, min_col_width=col_width, data_format=entry_format, row_first=False)


def print_best_picks(hero_names, best_by_pos, player_wrs):
    """Prints the aggregate value and player's win rate for best hero picks for each position.
    The hero data consist of hero ID, average counter value, average synergy value and the averaged value of previous metrics.
    
    Args:
        hero_names (dict{int: str}): Dictionary of hero names for hero indexes
        best_by_pos (list[list[tuple]]): List of hero aggregate values (id, avg counter, avg synergy, combined avg) for each position
        player_wrs (json): Object containing player's win rates for each hero (obtained through queries.get_player_winrates function)
    """
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
        best = best_by_pos[pos]
        if len(best) == 0:
            continue
        print(f'POSITION {pos+1}:')
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
    """Prints the json containing information on each hero. Used to find the IDs of heroes.
    
    Args:
        heroes (json): Information on heroes (obtained through queries.make_hero_info_query)
    """
    import json
    formatted = json.dumps(heroes, indent=2)
    print(formatted)
