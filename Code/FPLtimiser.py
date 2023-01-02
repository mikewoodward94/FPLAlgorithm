import pandas as pd
import pulp

def fpl_optimiser(projected_scores_for_optimiser, transfers, in_bank):
    '''
    Creates excel workbook of optimal squad/starters/captain for each week with FPL transfer logic.
    '''
    print("Starting Optimisation...")
    data = projected_scores_for_optimiser
    
    player_ids = data.index
    
    weeks = len(data.columns[5:-25])  
    free_transfers = transfers
    bank = in_bank
    columns = data.columns[5:-25]
    
    squad_var = {i: {} for i in range(1,weeks+1)}
    start_var = {i: {} for i in range(1,weeks+1)}
    bench_var = {i: {} for i in range(1,weeks+1)}
    strong_bench_var = {i: {} for i in range(1,weeks+1)}
    cap_var = {i: {} for i in range(1,weeks+1)}
    both_var = {i: {} for i in range(1, weeks+1)}
    week = {i: {} for i in range(1,weeks+1)}
    a_transfers_var = {i: [] for i in range(1,weeks+1)}
    in_team = data['in_team']
    cost = data['now_cost']
    GK = data['GK']
    DEF = data['Def']
    MID = data['Mid']
    ATT = data['Att']
    team1 = data['team1']
    team2 = data['team2']
    team3 = data['team3']
    team4 = data['team4']
    team5 = data['team5']
    team6 = data['team6']
    team7 = data['team7']
    team8 = data['team8']
    team9 = data['team9']
    team10 = data['team10']
    team11 = data['team11']
    team12 = data['team12']
    team13 = data['team13']
    team14 = data['team14']
    team15 = data['team15']
    team16 = data['team16']
    team17 = data['team17']
    team18 = data['team18']
    team19 = data['team19']
    team20 = data['team20']
    
    #vars
    for a in range(1,weeks+1):
        a_transfers_var[a] = pulp.LpVariable("wk" + str(a) + "at",lowBound=0, upBound=2, cat='integer')
        for i in player_ids:
            squad_var[a][i] = pulp.LpVariable('wk' + str(a) + 'x' + str(i), cat='Binary')
            start_var[a][i] = pulp.LpVariable('wk' + str(a) + 'y' + str(i), cat='Binary')
            bench_var[a][i] = pulp.LpVariable('wk' + str(a) + 'be' + str(i), cat='Binary')
            strong_bench_var[a][i] = pulp.LpVariable('wk' + str(a) + 'sb' + str(i), cat='Binary')
            cap_var[a][i] = pulp.LpVariable('wk' + str(a) + 'z' + str(i), cat='Binary')
            both_var[a][i] = pulp.LpVariable('wk' + str(a) + '+' + 'wk' + str(a+1) + 'b' + str(i), cat='Binary')
            week[a][i] = data[columns[a-1]][i]

    prob = pulp.LpProblem("Optimiser", pulp.LpMaximize)
    
    #Objective
    prob += pulp.lpSum([((week[a][i] * start_var[a][i]) + (week[a][i] * cap_var[a][i]) + (0.1*week[a][i] * strong_bench_var[a][i]) ) for a in range(1,weeks+1) for i in player_ids])
    
    #15 in squad and 11 in starters and 1 captain, starters in squad, captain in starters
    for a in range(1,weeks+1):
        prob += pulp.lpSum([squad_var[a][i] for i in player_ids]) == 15
        prob += pulp.lpSum([start_var[a][i] for i in player_ids]) == 11
        prob += pulp.lpSum([bench_var[a][i] for i in player_ids]) == 4
        prob += pulp.lpSum([strong_bench_var[a][i] for i in player_ids]) == 2
        prob += pulp.lpSum([cap_var[a][i] for i in player_ids]) == 1
        prob += pulp.lpSum([both_var[a][i] for i in player_ids]) >= 13
        
        for i in player_ids:
            prob += start_var[a][i] <= squad_var[a][i]
            prob += bench_var[a][i] <= squad_var[a][i]
            prob += cap_var[a][i] <= start_var[a][i]
            prob += strong_bench_var[a][i] <= bench_var[a][i]
            prob += start_var[a][i] + bench_var[a][i] <= 1
    
    #week 1 only different to current team by max FT
    prob += pulp.lpSum([squad_var[1][i] * in_team[i] for i in player_ids]) >= 15 - free_transfers
    
    #initial amount of transfers is set accounting for wildcard
    if free_transfers == 15:
        prob += a_transfers_var[1] == 1
    else:
        prob += a_transfers_var[1] <= free_transfers + 1 - 15 + pulp.lpSum([squad_var[1][i] * in_team[i] for i in player_ids])
    
    #amount of transfers available can't be 0 after initial
    for a in range(1,weeks+1):
        prob += a_transfers_var[a] >= 1
    
    #transfer rules(max 2 a week, accrue 1 a week + starting n) + limit no. of changes to available transfers
    for a in range(1,weeks):
        prob += a_transfers_var[a+1] <= a_transfers_var[a] + 1 - 15 + pulp.lpSum([both_var[a][i] for i in player_ids])
        prob += 15 - pulp.lpSum([both_var[a][i] for i in player_ids]) <= a_transfers_var[a]
    
        for i in player_ids:
            prob += squad_var[a+1][i] >= both_var[a][i]
            prob += squad_var[a][i] >= both_var[a][i]
            
        prob += pulp.lpSum(
        [15 - pulp.lpSum([both_var[b][i] for i in player_ids])
        for b in range(1, a+1)]) <= a - 1 + a_transfers_var[1]
    
    #cost can't be more than current value + bank
    for a in range(1,weeks+1):
        prob += pulp.lpSum([squad_var[a][i] * cost[i] for i in player_ids]) <= sum([in_team[i] * cost[i] for i in player_ids]) + bank
    
    #squad has 2 gk, 5 def, 5 mid, 3 att, starting team has 1 gk, 3-5 def, 2-5 mid, 1-3 att
    for a in range(1,weeks+1):
        prob += pulp.lpSum([strong_bench_var[a][i] * GK[i] for i in player_ids]) == 0
        prob += pulp.lpSum([squad_var[a][i] * GK[i] for i in player_ids]) == 2
        prob += pulp.lpSum([squad_var[a][i] * DEF[i] for i in player_ids]) == 5
        prob += pulp.lpSum([squad_var[a][i] * MID[i] for i in player_ids]) == 5
        prob += pulp.lpSum([squad_var[a][i] * ATT[i] for i in player_ids]) == 3
        
        prob += pulp.lpSum([start_var[a][i] * GK[i] for i in player_ids]) == 1
        prob += pulp.lpSum([start_var[a][i] * DEF[i] for i in player_ids]) >= 3
        prob += pulp.lpSum([start_var[a][i] * DEF[i] for i in player_ids]) <= 5
        prob += pulp.lpSum([start_var[a][i] * MID[i] for i in player_ids]) >= 2
        prob += pulp.lpSum([start_var[a][i] * MID[i] for i in player_ids]) <= 5
        prob += pulp.lpSum([start_var[a][i] * ATT[i] for i in player_ids]) >= 1
        prob += pulp.lpSum([start_var[a][i] * ATT[i] for i in player_ids]) <= 3
    
    #squad has max of 3 players of any PL team
    for a in range(1,weeks+1):
        prob += pulp.lpSum([squad_var[a][i] * team1[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team2[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team3[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team4[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team5[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team6[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team7[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team8[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team9[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team10[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team11[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team12[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team13[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team14[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team15[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team16[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team17[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team18[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team19[i] for i in player_ids]) <= 3
        prob += pulp.lpSum([squad_var[a][i] * team20[i] for i in player_ids]) <= 3
        
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team1[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team1[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team2[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team2[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team3[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team3[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team4[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team4[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team5[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team5[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team6[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team6[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team7[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team7[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team8[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team8[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team9[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team9[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team10[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team10[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team11[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team11[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team12[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team12[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team13[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team13[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team14[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team14[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team15[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team15[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team16[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team16[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team17[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team17[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team18[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team18[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team19[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team19[i] for i in player_ids]) <= 2
        prob += pulp.lpSum([squad_var[a][i] * GK[i] * team20[i] for i in player_ids]) + pulp.lpSum([squad_var[a][i] * DEF[i] * team20[i] for i in player_ids]) <= 2
    
    prob.solve(pulp.GLPK_CMD(timeLimit=900))
    print(pulp.LpStatus[prob.status])
    
    output = data[['element', 'name', 'now_cost', 'in_team']]
    
    squad = {i: {} for i in range(1,weeks+1)}
    start = {i: {} for i in range(1,weeks+1)}
    strong_bench = {i: {} for i in range(1,weeks+1)}
    cap = {i: {} for i in range(1,weeks+1)}
    
    squad_col = []
    start_col = []
    strong_bench_col = []
    cap_col = []
    
    for a in range(0, weeks):
        squad_col.append('squad_' + columns[a])
        start_col.append('start_' + columns[a])
        strong_bench_col.append('strong_bench_' + columns[a])
        cap_col.append('cap_' + columns[a])
    
    for a in range(1,weeks+1):
        for i in player_ids:
            squad[a][i] = squad_var[a][i].varValue
            start[a][i] = start_var[a][i].varValue
            strong_bench[a][i] = strong_bench_var[a][i].varValue
            cap[a][i] = cap_var[a][i].varValue
    
    squad_df = pd.DataFrame(squad)
    squad_df.columns = squad_col
    squad_df['element'] = output['element'] 
    squad_df = squad_df.loc[(squad_df.iloc[:,:-1] != 0).any(axis=1)]
    squad_df = pd.merge(output, squad_df, on=['element'], how='right')
    
    start_df = pd.DataFrame(start)
    start_df.columns = start_col
    start_df['element'] = output['element'] 
    start_df = start_df.loc[(start_df.iloc[:,:-1] != 0).any(axis=1)]
    start_df = pd.merge(output, start_df, on=['element'], how='right')
    
    strong_bench_df = pd.DataFrame(strong_bench)
    strong_bench_df.columns = strong_bench_col
    strong_bench_df['element'] = output['element'] 
    strong_bench_df = strong_bench_df.loc[(strong_bench_df.iloc[:,:-1] != 0).any(axis=1)]
    strong_bench_df = pd.merge(output, strong_bench_df, on=['element'], how='right')
    
    cap_df = pd.DataFrame(cap)
    cap_df.columns = cap_col 
    cap_df['element'] = output['element'] 
    cap_df = cap_df.loc[(cap_df.iloc[:,:-1] != 0).any(axis=1)]
    cap_df = pd.merge(output, cap_df, on=['element'], how='right')
    
    writer = pd.ExcelWriter('../Output/optimal_teams.xlsx', engine = 'xlsxwriter')
    squad_df.to_excel(writer, sheet_name = 'Squad', index=False)
    start_df.to_excel(writer, sheet_name = 'Start', index=False)
    strong_bench_df.to_excel(writer, sheet_name = 'StrongBench', index=False)
    cap_df.to_excel(writer, sheet_name = 'Captain', index=False)
    writer.save()
    
if __name__ == '__main__':
    fpl_optimiser()
