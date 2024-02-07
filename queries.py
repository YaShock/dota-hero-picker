import aiohttp
import socket
from misc import Error


def make_hero_info_query():
    return f'''
        {{
          constants {{
            heroes {{
              id,
              name,
              shortName,
              displayName
            }}
          }}
        }}
    '''


def make_match_query(matchid):
    return f'''
        {{
          match(id: {matchid}) {{
            id,
            players {{
              isRadiant,
              hero {{
                id,
                name
              }}
            }}
          }}
        }}
    '''


def make_hero_matchup_query(hero_id, bracket):
    return f'''
        {{
          heroStats {{
            heroVsHeroMatchup(heroId: {hero_id}, bracketBasicIds: [{bracket}]) {{
              advantage {{
                heroId,
                vs {{
                  heroId1,
                  heroId2,
                  synergy
                }},
                with {{
                  heroId1,
                  heroId2,
                  synergy
                }}
              }}
            }}
          }}
        }}
    '''


def make_heroes_matchup_query(bracket, heroes, hero_count):
    return f'''
        {{
          heroStats {{
            matchUp(heroIds: {heroes}, bracketBasicIds: [{bracket}], take: {hero_count}) {{
              heroId,
              vs {{
                heroId1,
                heroId2,
                synergy
              }},
              with {{
                heroId1,
                heroId2,
                synergy
              }}
            }}
          }}
        }}
    '''


def make_all_heroes_matchup_query(bracket, hero_count):
    return f'''
        {{
          heroStats {{
            matchUp(bracketBasicIds: [{bracket}], take: {hero_count}) {{
              heroId,
              vs {{
                heroId1,
                heroId2,
                synergy
              }},
              with {{
                heroId1,
                heroId2,
                synergy
              }}
            }}
          }}
        }}
    '''


def make_hero_winrate_query(pos, bracket):
    return f'''
        {{
            heroStats {{
                winWeek(
                    take: 1,
                    bracketIds: [{bracket}],
                    gameModeIds: [ALL_PICK_RANKED],
                    positionIds: [POSITION_{pos}]
                ) {{
                    heroId,
                    matchCount,
                    winCount
                }}
            }}
        }}
    '''


def make_player_winrates_query(player_id, hero_count):
    return f'''
        {{
          player(steamAccountId: {player_id}) {{
            matchCount,
            heroesPerformance(take: {hero_count}, request: {{
              take: 1000
            }}) {{
              heroId,
              winCount,
              matchCount
            }}
          }}
        }}
    '''


async def run_query(query, stratz_token):
    connector = aiohttp.TCPConnector(
        family=socket.AF_INET,
        ssl=False,
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        async def make_request(api):
            resp = await session.get(
                f'{api}?query={query}',
                headers = {
                    'Authorization': f'Bearer {stratz_token}',
                    'content-type': 'application/json'
                }
            )

            return await resp.json()

        try:
            data = (await make_request('https://api.stratz.com/graphql'))['data']
        except:
            try:
                data = (await make_request('https://apibeta.stratz.com/graphql'))['data']
            except Exception as e:
                raise Error(f'Failed to parse data from Stratz. The API may be down, your connection unstable, '
                            f'or something else. Exact error:\n\n{e}\n\nData:{data}')
        return data
