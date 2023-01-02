import requests
import pandas as pd

FLAGGEDLIST = '/home/McSpoish/flagged_players.csv'

def fpl_flagged():
    '''
    Creates a list of players who were flagged by gameweek(gw)/event/round.
    This is so that they can be removed from the historic data so players returning
    from injury etc aren't unfairly penalised for being flagged.

    Returns:
        Dataframe: element, round

    '''
    flagged_list = pd.read_csv(FLAGGEDLIST)

    current_status = get_current_player_status()
    current_flagged_players = current_status.loc[current_status['status'].isin(['i','d'])]

    players = get_current_gw_player_info()

    current_flagged_players = pd.merge(players, current_flagged_players, left_on=['element'], right_on=['id'], how='right').drop('id',1)
    current_flagged_players = current_flagged_players.loc[current_flagged_players['minutes'] < 45]
    current_flagged_players = current_flagged_players[['element','round']].drop_duplicates()

    flagged_players = pd.concat([flagged_list, current_flagged_players]).drop_duplicates()

    flagged_players.to_csv('/home/McSpoish/flagged_players.csv', index = None)

def get_current_player_status():
    '''
    Retrieves current status of each player
    Returns:
        Dataframe: element, status
    '''
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(url)
    json = r.json()
    elements_df = pd.DataFrame(json['elements'])
    status = elements_df[['id', 'status']]

    return(status)

def get_current_gw_player_info():
    '''
    Retrieves information from the current gw
    Returns:
        Dataframe: element, event, minutes
    '''
    no_of_players = get_no_of_players()
    player_data = []

    for i in range(1, 570 + 1):
        p_url = "https://fantasy.premierleague.com/api/element-summary/"+str(i)+"/"
        rp = requests.get(p_url)
        jsonp = rp.json()
        data = pd.DataFrame(jsonp['history'])
        data = data[['element', 'round', 'minutes']]
        player_data.append(data)

    player_data=pd.concat(player_data)

    gw = get_current_gw()
    players = player_data.loc[player_data['round'] == gw]

    return(players)

def get_current_gw():
    '''
    Returns: Current gameweek/event
    '''
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(url)
    json = r.json()
    events_df = pd.DataFrame(json['events'])
    current_gw = events_df.loc[events_df['is_current'] == True]['id'].iloc[0]

    return(current_gw)

def get_no_of_players():
    '''
    Returns the number of football players with data for this season.
    '''
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(url)
    json = r.json()
    elements = pd.DataFrame(json['elements'])
    return(len(elements))

if __name__ == '__main__':
    fpl_flagged()
