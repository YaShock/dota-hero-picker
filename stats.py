def calc_adv_matrix(radiant_heroes, dire_heroes, matchups_rad):
    mat = [[0 for col in range(5)] for row in range(5)]

    dire_idx = {}
    for idx in range(0, 5):
        dire_idx[dire_heroes[idx]['id']] = idx

    for rad_idx, matchups in enumerate(matchups_rad):
        data = matchups['heroStats']['heroVsHeroMatchup']['advantage'][0]['vs']
        for matchup in data:
            if matchup['heroId2'] in dire_idx:
                idx = dire_idx[matchup['heroId2']]
                mat[rad_idx][idx] = matchup['synergy']

    return mat


def get_best_heroes_by_pos(pos_win_rates, pick_thr=0.05, hero_count=10):
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


def get_best_pick_by_pos(meta_heroes, hero_names, meta_matchups, radiant_heroes, dire_heroes, stratz_token, is_radiant=True, pos=None):
    if pos is None:
        pos = [1, 2, 3, 4, 5]
    all_meta_heroes = set()

    for p in range(0, 5):
        for hero in meta_heroes[p]:
            all_meta_heroes.add(hero[0])

    against_idx = dire_heroes if is_radiant else radiant_heroes
    with_idx = radiant_heroes if is_radiant else dire_heroes

    print("WITH: " + ', '.join([hero_names[hero] for hero in with_idx]))
    print("AGAINST: " + ', '.join([hero_names[hero] for hero in against_idx]))

    best_heroes = {}
    for hero in all_meta_heroes:
        # Can't pick already picked heroes
        if hero in against_idx or hero in with_idx:
            continue

        matchups = meta_matchups[hero]
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


# meta_heroes has to be sorted before and after
# include_ids: list of hero ids to be included
# pos_win_rates: list of list of tuples (hero id, match count, win count) for each position
# meta_heroes: best heroes for each position, list of lists of tuples (id, winrate)
def include_heroes(meta_heroes, include_ids, hero_count, pos_win_rates):
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

        # fill the rest with meta heroes if they are not already in there
        incl_count = len(incl_data)
        meta_i = hero_count - 1

        while incl_count < hero_count:
            hero_id, wr = meta_heroes[pos][meta_i]
            if hero_id not in incl_slice:
                incl_data.append((hero_id, wr))
                incl_count += 1
            meta_i -= 1

        meta_incl_heroes[pos] = sorted(incl_data, key=lambda x: x[1], reverse=True)

    return meta_incl_heroes


def get_user_winrates():
    pass
