import requests
import pandas as pd
import numpy as np

from FPLtimiser import fpl_optimiser
import FPLgraph


team_id = 
gameweeks = 8
transfers = 1
in_bank = 10


def fpl_algorithm(team_id, gameweeks, transfers, in_bank):
    '''
    The aim of this project was to see how well an algorithm could do purely using fpl points.
    
    Calculates projected scores for each player for each gameweek(gw)/event/round
    and uses this to create optimal an optimal FPL team. Utilises existing teams,
    amount in bank, and available transfers.
    
    Projected scores for each player are calculated using a weighted average points per match
    from the previous 8 gameweeks (number under review, 8 chosen to capture form).
    The average points are weighted by opposing team difficulty. Team difficulties are
    split in to gk/def/att as some teams have strong offense but weak defense (or any permutation)
    meaning attackers may do well but defenders not. These team ratings are simply calculated
    as an average of the fpl points scored against them per game. The projections are
    calculated by combining the players historical scoring with their future opponents.
    
    These scores are then fed in to an optimiser that satisfies FPL logic such as position or
    team limits on players. This produces an excel workbook of squad, starting team, and captain
    for each week. Additionally visualisations are produced for fun.

    '''
    player_data, fixtures = get_player_data(gameweeks)
    player_data = remove_flagged_players(player_data)
    
    projected_scores = calculate_projected_scores(player_data, fixtures)
    projected_scores_for_optimiser = prepare_for_optimiser(projected_scores, team_id)
    
    fpl_optimiser(projected_scores_for_optimiser, transfers, in_bank)
    FPLgraph.fpl_graphs(projected_scores_for_optimiser, player_data)
    print("Complete!")

def get_player_data(gameweeks):
    '''
    Connects to the FPL API and gets the necessary information for the algorithm.
    
    Args:
        gameweeks: The number of past gameweeks that are taken in to consideration
    Returns: A dataframe holding recent useful historical data from this season split by games for each player.
    [Element, Round, Opponent Team, Total Points, Minutes, Element Type, Team Code, First Name, Second Name, Web Name, Position]
        A second dataframe of players future fixtures
    [Team Home, Team Away, Event, Is Home, Element, First Name, Second Name, Web Name, Element Type, Opponent Team]
    '''
    no_of_players = get_no_of_players()
    player_data = []
    fixtures = []
    
    for i in range(1, no_of_players + 1):
        p_url = "https://fantasy.premierleague.com/api/element-summary/"+str(i)+"/"
        rp = requests.get(p_url)
        jsonp = rp.json()
        data = pd.DataFrame(jsonp['history'])
        data = data[['element', 'round', 'opponent_team', 'total_points', 'minutes']]
        player_data.append(data)
        
        fdata=pd.DataFrame(jsonp['fixtures'])
        fdata["element"] = i
        fdata=fdata[["team_h", "team_a", "event", "is_home", "element"]]
        fixtures.append(fdata)
        
    player_data=pd.concat(player_data)
    
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(url)
    json = r.json()
    elements = pd.DataFrame(json['elements'])
    elements = elements[['id', 'element_type', 'team_code', 'first_name', 'second_name', 'web_name']]
    
    player_data=pd.merge(player_data, elements, left_on=['element'], right_on=['id'], how='left').drop('id',1)
    
    player_data['position'] = np.select(
        [
        player_data['element_type'] == 1,
        player_data['element_type'] == 2,
        player_data['element_type'] == 3,
        player_data['element_type'] == 4
        ],
        [
        'GK',
        'Defense',
        'Attack',
        'Attack'
        ], 'other'
        )
    
    earliest_gw = player_data['round'].max() - gameweeks
    player_data = player_data.loc[player_data['round'] > earliest_gw]
    
    fixtures=pd.concat(fixtures)
    elements = pd.DataFrame(json['elements'])
    id_name = elements[['id', 'first_name', 'second_name', 'web_name', 'element_type']]
    fixtures = pd.merge(fixtures, id_name, left_on=['element'], right_on=['id'], how='left').drop('id',1)
    fixtures['opponent_team']= np.where(fixtures['is_home'] == True, fixtures['team_a'], fixtures['team_h'])
    
    return(player_data, fixtures)

def remove_flagged_players(player_data):
    '''
    Removes gameweeks where player was flagged and thus didn't play.
    This list is generated from FPLflagged.py which is hosted on pythonanywhere.com
    to ensure it runs every day.
    
    Args:
        Dataframe: Historical player data
    
    Returns:
        Dataframe: Same as Arg except with flagged player gameweeks removed
    '''
    flagged_players = pd.read_csv('../Data/flagged_players.csv')
    
    player_data = pd.merge(player_data, flagged_players, how='left' ,on=['element','round'], indicator=True)
    player_data = player_data.loc[player_data['_merge'] == 'left_only']
    player_data = player_data.drop(columns=['_merge'])
    
    return(player_data)
    

def calculate_team_rating(player_data, position):
    '''
    Calculates normalised ratings for each team for each position, a rating of relative difficulty.
    For example Man City will have a low rating because generally not many points are scored against them.
    
    Args:
        player_data: See get_player_data
        position: GK, Defense, or Attack. Choose which position to calculate team rating for.
    Returns: A dataframe with the rating for that position by team.
    [Team, Points Against Per Game, Normalised Rating]
    '''
    team_points_against = player_data.groupby(['position', 'opponent_team'])['total_points'].sum().reset_index()
    matches = player_data.drop_duplicates(['round', 'opponent_team', 'position']).groupby(['position', 'opponent_team']).agg(matches=('opponent_team', 'count')).reset_index()
    team_points_against['matches'] = matches['matches']
    team_points_against['points_against_per_game'] = team_points_against['total_points']/team_points_against['matches']
    
    average_points = team_points_against.loc[team_points_against['position'] == position]['points_against_per_game'].mean()
    
    rating = team_points_against.loc[team_points_against['position'] == position][['opponent_team', 'points_against_per_game']]
    rating['normalised'] = rating['points_against_per_game']/average_points
    return(rating)
    
def calculate_player_rating(player_data, position, team_rating):
    '''
    Calculates the rating for each player.
    Average points over the last n gameweeks adjusted for average opponent difficulty.
    Two times the coefficient of variation is subtracted from this to reward consistent points.
    The number of minutes a player plays is also taken in to account to reward consistent minutes.
    
    Args:
        player_data: See get_player_data
        position: GK, Defense, or Attack. Choose which position to calculate player rating for.
        team_rating: See get_team_rating
    Returns: A dataframe with the score for each player
    [Element, Points Per Match, Score]
    '''
    player = pd.merge(player_data[player_data['position'] == position], team_rating, left_on=['opponent_team'], right_on=['opponent_team'], how='left').drop('points_against_per_game',1)
    player = player[['element', 'round', 'opponent_team', 'total_points', 'normalised', 'minutes']]
    player['minute_mult'] = np.select(
        [player['minutes'] >= 60, (player['minutes'] > 0) & (player['minutes'] < 60), player['minutes'] == 0],
        [1, 0.5, 0]
        )
    player_total = player.groupby('element')["total_points"].sum().reset_index()
    player_matches = player.groupby('element').agg(matches=('total_points', 'count')).reset_index()
    player_minmult = player.groupby('element')['minute_mult'].sum().reset_index()
    player_total['matches'] = player_matches['matches']
    player_total['minute_mult'] = player_minmult['minute_mult']/player_total['matches']
    player_total['minutes'] = player.groupby('element')['minutes'].sum().reset_index()['minutes']
    player_total['opp_dif'] = player.groupby('element')['normalised'].mean().reset_index()['normalised']
    player_total['points_per_match'] = player_total['total_points']/player_total['opp_dif']/player_total['matches']
    player_total['points_per_match'] = player_total['points_per_match'] * player_total['minute_mult']
    player_total['points_per_match'] = np.select(
        [player_total['minutes'] >= 180, player_total['minutes'] < 180],
        [player_total['points_per_match'], 0]
        )
    player_total['std'] = player.groupby('element')['total_points'].std().reset_index().rename(columns = {'total_points': 'std'})['std']
    player_total['cov'] = player_total['std']/player_total['points_per_match']
    player_total['cov'] = player_total['cov'].apply(lambda x: (abs(x) + x)/2)
    player_total['score'] = player_total['points_per_match'] - 2*player_total['cov']
    player_total['score'] = player_total['score'].apply(lambda x: (abs(x) + x)/2)
    
    player_ppg=player_total[['element', 'score']]
    return(player_ppg)

def assign_positional_ratings(player_data, position, fixtures):
    '''
    Assigns the rating of future opposing teams dependent on position.
    
    Args: player_data: see get_player_data
            position: position rating to be assigned
    Return: a dataframe of for each players gameweek with opposing team rating
    '''
    rating = calculate_team_rating(player_data, position)
    ppg = calculate_player_rating(player_data, position, rating)
    fixtures = pd.merge(fixtures, ppg, left_on=['element'], right_on=['element'], how='inner').fillna(0)
    fixtures = pd.merge(fixtures, rating, left_on=['opponent_team'], right_on=['opponent_team'], how='left')
    return(fixtures)

def calculate_projected_scores(player_data, fixtures):
    '''
    Calculates projected scores for each player for each future fixture.
    This is based on player rating and opposing team rating.
    
    Args: player_data, fixtures: see get_player_data
    Returns: A dataframe of projected points per player per fixture
    [Element, First Name, Second Name, Web Name, Element Type, Event, Projected Points, Score]
    
    '''
    attack_fixtures = assign_positional_ratings(player_data, 'Attack', fixtures)
    defense_fixtures = assign_positional_ratings(player_data, 'Defense', fixtures)
    gk_fixtures = assign_positional_ratings(player_data, 'GK', fixtures)
    fixtures = pd.concat([attack_fixtures, defense_fixtures, gk_fixtures])
    
    fixtures['projected_score'] = fixtures['score'] * fixtures['normalised']

    projection = fixtures[['element', 'first_name', 'second_name', 'web_name', 'element_type', 'event', 'projected_score']]
    projection = projection.loc[projection['event'] != 0]
    return(projection)

def prepare_for_optimiser(projected_scores, team_id):
    '''
    Final data preparations for the optimiser, includes:
        Adding cost and team of each player
        Reducing projected score based on status (injuries etc)
        Transforming so that each player is a row and predicted gw scores are columns
        Adding if player is in current fpl team
        0 or 1 columns for in each team and in each position
        
    Args: projected scores, dataframe of fixture by fixture projected scores for each player
    Returns: dataframe of fixture by fixture projected scores for each player ready for optimiser
    
    '''
    data = projected_scores
    
    data["name"] = data["first_name"] + " " + data["web_name"]
    data=data.drop(["first_name", "web_name"], axis=1)
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(url)
    json = r.json()
    elements_df = pd.DataFrame(json['elements'])
    elements_df = elements_df[['id', 'now_cost', 'team', 'status']]

    data=pd.merge(data, elements_df, left_on=["element"], right_on=["id"], how="left").dropna()
    data=data.drop(["id"], axis=1)

    data["projected_score"] = np.select(
        [data["status"] == "i", data["status"] == "d", data["status"] == "a"],
        [0, data["projected_score"] * 0.5, data["projected_score"]]
        )


    data = data.groupby(['element', 'name', 'element_type', 'now_cost', 'team', 'event'])['projected_score'].sum().unstack().reset_index()

    #changing column names from numbers to strings
    a = data.columns[5:]
    b = ['w' + str(int(a[i])) for i in range(0, len(a))]
    d = dict(zip(a,b))
    data = data.rename(columns=d)

    current_team = get_current_team(team_id)
    data=pd.merge(data, current_team, on=['element'], how='left')
    data = data.fillna(0)

    # create new column for each team
    for i in range(1,21):
        team = "team" + str(i)
        data[team] = np.where(data["team"] == i, 1, 0)

    #create new columns that has 1 or 0 if player == a specific position
    data['GK'] = (data['element_type'] == 1).astype(float)
    data['Def'] = (data['element_type'] == 2).astype(float)
    data['Mid'] = (data['element_type'] == 3).astype(float)
    data['Att'] = (data['element_type'] == 4).astype(float)
    
    data.to_csv('../Data/ready_projections.csv', index = None)
    print('Projections Ready!')
    return(data)

def get_current_team(team_id):
    '''
    Calls the FPL API to return the current players in the team.
    
    Args: team_id, FPL ID of the team that the algorithm is running for
    Returns: Players currently in this team
    '''
    gw_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(gw_url)
    json = r.json()
    events_df = pd.DataFrame(json['events'])
    next_gw = events_df.loc[events_df['is_next'] == True]['id'].iloc[0]
    
    team_url = "https://fantasy.premierleague.com/api/entry/"+str(team_id)+"/event/"+str(next_gw-1)+"/picks/"
    r = requests.get(team_url)
    json = r.json()
    current_team = pd.DataFrame(json['picks'])
    current_team['in_team'] = 1
    current_team = current_team[['element', 'in_team']]
    return(current_team)

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
    fpl_algorithm(team_id, gameweeks, transfers, in_bank)
