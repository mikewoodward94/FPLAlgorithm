import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
import seaborn as sns
import colorcet as cc
import mplcursors
import requests

import FPLgorithm

LEAGUE_ID = ''

clubs_2021 = ["Arsenal",
              "Aston Villa",
              "Brentford",
              "Brighton & Hove Albion",
              "Burnley",
              "Chelsea",
              "Crystal Palace",
              "Everton",
              "Leicester City",
              "Leeds United",
              "Liverpool",
              "Manchester City",
              "Manchester United",
              "Newcastle United",
              "Norwich City",
              "Southampton",
              "Tottenham Hotspur",
              "Watford",
              "West Ham United",
              "Wolverhampton Wanderers"]

def fpl_graphs(projected_scores_for_optimiser, player_data):
    '''
    Creates visualisations of the projected scores, team ratings, and league positions
    '''
    
    fig1_data = prep_for_fig1(projected_scores_for_optimiser)
    fig1_costVSscore(fig1_data)
    
    fig2_data = prep_for_fig2(player_data)
    fig2_attackVSdefense(fig2_data)
  
    fig3_data = prep_for_fig3()
    fig3_overallrank(fig3_data)
    
    
def fig1_costVSscore(data):
    palette = sns.color_palette(cc.glasbey, n_colors=20)
    plt.figure('Cost Vs Score', figsize=(18,9))
    sns.set(style="ticks")
    sns.set_context("talk")
    sns.scatterplot(data = data, x = 'Cost', y = 'total_score', hue = 'Club', style = 'Position', palette = palette, s = 250)
    sns.despine()
    plt.xlabel("Cost (£m's)")
    plt.ylabel("Score (FPLgorithm)")
    plt.legend(bbox_to_anchor=(1.05, 1), borderaxespad=0.)
    plt.tight_layout()
    cr = mplcursors.cursor(hover=True)
    cr.connect('add', lambda sel: sel.annotation.set_text(data['name'][sel.index]))

def fig2_attackVSdefense(data):
    palette = sns.color_palette(cc.glasbey, n_colors=20)
    fig = plt.figure('Attack vs Defense', figsize=(18,9))
    ax = fig.add_subplot()
    sns.set(style="ticks")
    sns.set_context("talk")
    sns.scatterplot(data = data, x = 'attack', y = 'defense', hue = 'Club', palette = palette, s = 400)
    sns.despine()
    anc1 = AnchoredText('Weak Attack / Strong Defense', loc = 'upper left', frameon = False)
    anc2 = AnchoredText('Weak Attack / Weak Defense', loc = 'upper right', frameon = False)
    anc3 = AnchoredText('Strong Attack / Strong Defense', loc = 'lower left', frameon = False)
    anc4 = AnchoredText('Strong Attack / Weak Defense', loc = 'lower right', frameon = False)
    ax.add_artist(anc1)
    ax.add_artist(anc2)
    ax.add_artist(anc3)
    ax.add_artist(anc4)
    plt.axhline(y=1)
    plt.axvline(x=1)
    plt.xlabel("Attack Rating")
    plt.ylabel("Defense Rating")
    plt.legend(bbox_to_anchor=(1.05, 1), borderaxespad=0.)
    plt.tight_layout()
    
def fig3_overallrank(data):
    fig = plt.figure('Overall Rank', figsize=(18,9))
    sns.set(style="ticks")
    sns.set_context("talk")
    sns.lineplot(data = data , x = 'event', y = 'overall_rank', hue = 'player_name')
    sns.despine()
    plt.xlabel("Event")
    plt.ylabel("Overall Rank")
    plt.legend(bbox_to_anchor=(1.05, 1), borderaxespad=0.)
    plt.tight_layout()

if __name__ == '__main__':
    fpl_graphs()
    
def prep_for_fig1(projected_scores_for_optimiser):
    data = projected_scores_for_optimiser.iloc[:, :-25]
    data = data.loc[(data == 0).sum(axis=1) < len(data.columns[5:])].reset_index()
    data['total_score'] = data.iloc[:, 6:].sum(axis=1)
    
    data['Position'] = np.select(
        [
        data['element_type'] == 1,
        data['element_type'] == 2,
        data['element_type'] == 3,
        data['element_type'] == 4
        ],
        [
        'Goalkeeper',
        'Defense',
        'Midfield',
        'Striker'
        ], 'other'
        )
    
    data['Club'] = data['team'].apply(lambda x: clubs_2021[x-1])
    
    data['Cost'] = data['now_cost']/10
    return(data)

def prep_for_fig2(player_data):
    defense = FPLgorithm.calculate_team_rating(player_data, 'Defense')
    defense = defense[['opponent_team', 'normalised']].rename(columns={'opponent_team': 'team', 'normalised': 'defense'})
    attack = FPLgorithm.calculate_team_rating(player_data, 'Attack')
    attack = attack[['opponent_team', 'normalised']].rename(columns={'opponent_team': 'team', 'normalised': 'attack'})
    
    team_ratings = pd.merge(defense, attack, on = 'team')
    team_ratings['Club'] = team_ratings['team'].apply(lambda x: clubs_2021[x-1])
    
    return(team_ratings)

def prep_for_fig3():
    url = "https://fantasy.premierleague.com/api/leagues-classic/" + LEAGUE_ID + "/standings/"
    r = requests.get(url)
    json = r.json()
    league_df = pd.DataFrame(json['standings'])
    league_df = league_df["results"]
    league_df = pd.DataFrame.from_records(league_df)
    league_df = league_df[["entry", "player_name", "entry_name"]]
    
    team_df = []
    
    for i in league_df["entry"]:
        url2 = "https://fantasy.premierleague.com/api/entry/" + str(i) + "/history/"
        r2 = requests.get(url2)
        json2 = r2.json()
        data = pd.DataFrame(json2['current'])
        data["entry"] = i
        team_df.append(data)
    
    team_df = pd.concat(team_df)
    
    team_df = pd.merge(team_df, league_df, left_on=["entry"], right_on=["entry"], how="left")
    team_df = team_df[['event', 'overall_rank', 'player_name']]
    team_df = team_df[team_df['player_name'] != 'Fergus Cowie']
    return(team_df)
