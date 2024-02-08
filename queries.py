import aiohttp
import socket
from misc import Error


def make_hero_info_query():
    """Creates a query string for hero information (their ID and 3 different types of name).
    
    Returns:
        str: query string
    """
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
    """Creates a query string for match information (its ID, each players' team and hero).
    
    Args:
        matchid (long): ID of the match queried
    
    Returns:
        str: query string
    """
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


def make_heroes_matchup_query(bracket, hero_count):
    """Creates a query string for counters and synergy values for each hero.
    
    Args:
        bracket (str): Bracket to query (from HERALD to combined DIVINE_IMMORTAL)
        hero_count (int): The number of hero matchups (counter and synergy each) for each hero
    
    Returns:
        str: query string
    """
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
    """Creates a query string for hero winrates of a given position.
    
    Args:
        pos (int): The position for hero winrates (from 1 to 5)
        bracket (str): Bracket to query (from HERALD to IMMORTAL)
    
    Returns:
        str: query string
    """
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
    """Creates a query string for all heroes of a given player.
    
    Args:
        player_id (long): Player's Steam ID
        hero_count (int): The number of heroes queried
    
    Returns:
        str: query string
    """
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
    """Creates connection to the Stratz's GraphQL API and executed the given query string.
    
    Args:
        query (str): Query string passed to GraphQL API
        stratz_token (str): Player's Stratz token
    
    Returns:
        json: Data of the query result
    
    Raises:
        Error: Error indicating failure to connect to the GraphQL API or erroneous query string
    """
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
