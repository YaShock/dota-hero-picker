def calc_adv_matrix(radiant_heroes, dire_heroes, hero_matchups):
    """Creates matrices for each radiant hero's counter value against each hero on dire, and synergy matrices between heroes on each team.
    
    Args:
        radiant_heroes (list[int]): List of hero indexes for radiant
        dire_heroes (list[int]): List of hero indexes for dire
        hero_matchups (dict{int: json}): Match up data for each hero ID (obtained through queries.make_heroes_matchup_query)
    
    Returns:
        tuple(list, list, list): 3 matrices (counters, synergy for radiant, synergy for dire)
    """
    mat_vs = [[0 for col in range(len(dire_heroes))] for row in range(len(radiant_heroes))]
    mat_with_rad = [[0 for col in range(len(radiant_heroes))] for row in range(len(radiant_heroes))]
    mat_with_dire = [[0 for col in range(len(dire_heroes))] for row in range(len(dire_heroes))]

    rad_idx = {}
    dire_idx = {}
    for idx in range(0, len(radiant_heroes)):
        rad_idx[radiant_heroes[idx]] = idx
    for idx in range(0, len(dire_heroes)):
        dire_idx[dire_heroes[idx]] = idx

    for hero in radiant_heroes:
        matchups = hero_matchups[hero]['vs']

        for matchup in matchups:
            if matchup['heroId2'] in dire_heroes:
                idx_1 = rad_idx[matchup['heroId1']]
                idx_2 = dire_idx[matchup['heroId2']]
                mat_vs[idx_1][idx_2] = matchup['synergy']

    for hero in radiant_heroes:
        matchups = hero_matchups[hero]['with']
        for matchup in matchups:
            if matchup['heroId2'] in radiant_heroes:
                idx_1 = rad_idx[matchup['heroId1']]
                idx_2 = rad_idx[matchup['heroId2']]
                mat_with_rad[idx_1][idx_2] = matchup['synergy']

    for hero in dire_heroes:
        matchups = hero_matchups[hero]['with']
        for matchup in matchups:
            if matchup['heroId2'] in dire_heroes:
                idx_1 = dire_idx[matchup['heroId1']]
                idx_2 = dire_idx[matchup['heroId2']]
                mat_with_dire[idx_1][idx_2] = matchup['synergy']


    return mat_vs, mat_with_rad, mat_with_dire


def get_best_heroes_by_pos(pos_win_rates, pick_thr=0.05, hero_count=10):
    """Returns the meta heroes for each given position based on their win rate. Meta is determined by the hero's pick rate for a given position.
    
    Args:
        pos_win_rates (list[json]): List of heroes' win rate for each position (obtained through queries.make_hero_winrate_query)
        pick_thr (float, optional): The pick rate threshold for including heroes in a given position
        hero_count (int, optional): The number of heroes for each position returned
    
    Returns:
        list[list[tuple(int, float)]]: List of IDs and win rates of best heroes for each position
    """
    poss = [[], [], [], [], []]

    for pos in range(0, 5):
        data = pos_win_rates[pos]['heroStats']['winWeek']
        all_match_count = sum([hero['matchCount'] for hero in data])

        for hero in data:
            pick_rate = hero['matchCount'] / (all_match_count / 10)
            if pick_rate >= pick_thr:
                wr = hero['winCount'] / hero['matchCount']
                poss[pos].append((hero['heroId'], wr))

    for pos, hero_list in enumerate(poss):
        poss[pos] = sorted(hero_list, key=lambda x: x[1], reverse=True)
        poss[pos] = poss[pos][:hero_count]

    return poss


def get_best_pick_by_pos(meta_heroes, hero_matchups, radiant_heroes, dire_heroes, is_radiant=True, pos=None):
    """Determines the best heroes based on overall best meta heroes and the picked heroes the given team.
    
    Args:
        meta_heroes (list[list[tuple(int, float)]]): List of best heroes (their ID and win rate) for each position
        hero_matchups (dict{int: json}): Match up data for each hero ID (obtained through queries.make_heroes_matchup_query)
        radiant_heroes (list[int]): List of hero indexes for radiant
        dire_heroes (list[int]): List of hero indexes for dire
        is_radiant (bool, optional): Determines if picking for radiant side
        pos (list[int], optional): List of positions to consider, by default includes all positions (1-5)
    
    Returns:
        list[list[tuple(int, float, float, float)]]: ID, avg counter, avg synergy, averaged value for each hero for each position
    """
    if pos is None:
        pos = [1, 2, 3, 4, 5]
    all_meta_heroes = set()

    for p in range(0, 5):
        for hero in meta_heroes[p]:
            all_meta_heroes.add(hero[0])

    against_idx = dire_heroes if is_radiant else radiant_heroes
    with_idx = radiant_heroes if is_radiant else dire_heroes

    best_heroes = {}
    for hero in all_meta_heroes:
        # Can't pick already picked heroes
        if hero in against_idx or hero in with_idx:
            continue

        matchups = hero_matchups[hero]
        data_cntr = matchups['vs']
        data_syn = matchups['with']
        
        counter, synergy = 0, 0

        for matchup in data_cntr:
            if matchup['heroId2'] in against_idx:
                counter += matchup['synergy'] / len(against_idx)

        for matchup in data_syn:
            if matchup['heroId2'] in with_idx:
                synergy += matchup['synergy'] / len(with_idx)

        val = (counter + synergy) / 2

        best_heroes[hero] = (counter, synergy, val)

    best_by_pos = [[], [], [], [], []]
    for p in pos:
        p -= 1
        for hero in meta_heroes[p]:
            hero_id = hero[0]
            # Can't pick already picked heroes
            if hero_id in against_idx or hero_id in with_idx:
                continue

            hero_stats = best_heroes[hero_id]
            best_by_pos[p].append((hero_id, hero_stats[0], hero_stats[1], hero_stats[2]))
        best_by_pos[p] = sorted(best_by_pos[p], key=lambda x: x[3], reverse=True)

    return best_by_pos


def include_heroes(meta_heroes, include_ids, hero_count, pos_win_rates):
    """Adds selected heroes to the current best meta heroes.
    
    Args:
        meta_heroes (list[list[tuple(int, float)]]): Best meta heroes obtained from get_best_heroes_by_pos
        include_ids (list[list[int]]): IDs of heroes to be included for each position
        hero_count (int): Number of meta heroes for each position
        pos_win_rates (list[json]): List of heroes' win rate for each position (obtained through queries.make_hero_winrate_query)
    
    Returns:
        list[list[tuple(int, float)]]: Updated and resorted list of heroes that include given heroes
    """
    meta_incl_heroes = meta_heroes[:]

    # Replace lowest winrate heroes with custom picks and sort again
    for pos in range(0, 5):
        incl_slice = include_ids[pos][:hero_count]
        data = pos_win_rates[pos]['heroStats']['winWeek']
        incl_data = []

        for hero in data:
            if hero['heroId'] in incl_slice:
                wr = hero['winCount'] / hero['matchCount']
                incl_data.append((hero['heroId'], wr))

        # Fill the rest with meta heroes if they are not already in there
        incl_count = len(incl_data)
        meta_i = 0

        while incl_count < hero_count:
            hero_id, wr = meta_heroes[pos][meta_i]
            if hero_id not in incl_slice:
                incl_data.append((hero_id, wr))
                incl_count += 1
            meta_i += 1

        meta_incl_heroes[pos] = sorted(incl_data, key=lambda x: x[1], reverse=True)

    return meta_incl_heroes
