from flask import Flask, request, send_from_directory
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import os

app = Flask(__name__, static_folder="../client/build", static_url_path="/")

# db_name = "my_database.db"
db_name = os.path.join("/tmp", "my_database.db")

def store_dataframe_to_sqlite(dataframe, table_name, if_exists='replace'):
    conn = sqlite3.connect(db_name)
    # Convert list and dictionary columns to JSON strings
    for col in dataframe.columns:
        if any(isinstance(item, (list, dict)) for item in dataframe[col]):
            dataframe[col] = dataframe[col].apply(json.dumps)
    dataframe.to_sql(table_name, conn, if_exists=if_exists, index=False)
    # conn.close()

def retrieve_dataframe_from_sqlite(table_name):
    try:
        conn = sqlite3.connect(db_name)
        dataframe = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        # conn.close()
        
        # Convert JSON strings back to lists and dictionaries safely
        for col in dataframe.columns:
            if dataframe[col].dtype == 'object':  # Only apply to string columns
                dataframe[col] = dataframe[col].apply(
                    lambda x: json.loads(x) if isinstance(x, str) and x.startswith(("{", "[")) else x
                )
        return dataframe
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None

memory_storage = {}

def get_ktc_rankings():
    base_url = "https://keeptradecut.com/dynasty-rankings"
    headers = {"User-Agent": "Mozilla/5.0"}
    players = []

    # Loop over pages (1 to 10, adjust the range as needed)
    for page in range(0, 9):  # You can change this to 1, 2, ..., 50 for 500 players
        url = f"{base_url}?page={page}&filters=QB|WR|RB|TE|RDP&format=2"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to retrieve page {page}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for player_row in soup.select(".onePlayer"):
            name_tag = player_row.select_one(".player-name a")
            rank_tag = player_row.select_one(".value")

            if name_tag and rank_tag:
                name = name_tag.text.strip()
                rating = rank_tag.text.strip()
                players.append((name, rating))

    df = pd.DataFrame(players, columns=["Player", "Rating"])
    
    unwanted_strings = [' Jr.', ' Sr.', ' III', ' II']
    for s in unwanted_strings:
        df['Player'] = df['Player'].str.replace(s, '', regex=False)
        
    # Unique cases
    df['Player'] = df['Player'].str.replace("D.J.", 'DJ', regex=False)
    df['Player'] = df['Player'].str.replace("D.J.", 'DJ', regex=False)
    df['Player'] = df['Player'].str.replace("Marquise", 'Hollywood', regex=False)
    df['Player'] = df['Player'].str.replace("Chigoziem", 'Chig', regex=False)
    df['Player'] = df['Player'].str.replace("Demario", 'DeMario', regex=False)
    
    df['Player_lower'] = df['Player'].str.lower()
    
    return df

def get_league_rosters(leagueId):
    # leagueId = memory_storage.get("league_id", 'No string found for this key')
    url = "https://api.sleeper.app/v1/league/" + leagueId + "/rosters";
    response = requests.get(url)
    json_data = json.loads(response.text)
    df = pd.DataFrame(json_data)
    return df;

def get_nfl_players():
    roster_df = retrieve_dataframe_from_sqlite("roster_df")
    url = "https://api.sleeper.app/v1/players/nfl";
    response = requests.get(url)
    json_data = json.loads(response.text)
    df = pd.DataFrame.from_dict(json_data, orient="index")
    df['sleeper_id'] = df.index
    df['full_name_lower'] = df['full_name'].str.lower()

    # drop players not rostered
    roster_players_list = roster_df['players'].apply(lambda x: x if isinstance(x, list) else [])
    all_roster_sleeper_ids = set()
    for player_list in roster_players_list:
        all_roster_sleeper_ids.update(player_list)
        
    df = df.drop(df[~df['sleeper_id'].isin(all_roster_sleeper_ids)].index)
    return df

# def get_roster_positions():
    url = "https://api.sleeper.app/v1/league/" + leagueId;
    response = requests.get(url)
    json_data = json.loads(response.text)
    roster_positions = json_data["roster_positions"]
    return roster_positions;

def get_all_sleeper_dfs(league_id):
    rankings_df = get_ktc_rankings();
    store_dataframe_to_sqlite(rankings_df, "rankings_df")
    # leagueId = memory_storage.get("league_id", 'No string found for this key')
    print("leagueID: ", league_id)
    roster_df = get_league_rosters(league_id);
    store_dataframe_to_sqlite(roster_df, "roster_df")
    print("stored roster_df")
    players_df = get_nfl_players();
    
    store_dataframe_to_sqlite(players_df, "players_df")
    print("stored players_df")
    league_users_df = get_league_users(league_id);
    store_dataframe_to_sqlite(league_users_df, "league_users_df")
    print("stored league_users_df")
    ranked_players_df = rankings_df.merge(players_df, left_on='Player', right_on='full_name', how='inner')
    store_dataframe_to_sqlite(ranked_players_df, "ranked_players_df")
    print("stored ranked_players_df")
    positional_strengths_df = get_positional_strengths();
    store_dataframe_to_sqlite(positional_strengths_df, "positional_strengths_df")
    print("stored positional_strengths_df")
    print("PROCESSED SLEEPER DATA")

def get_league_users(leagueId):
    # leagueId = memory_storage.get("league_id", 'No string found for this key')
    url = "https://api.sleeper.app/v1/league/" + leagueId + "/users";
    response = requests.get(url)
    json_data = json.loads(response.text)
    df = pd.DataFrame(json_data)
    return df;

def get_player_rating(sleeper_id, ranked_players_df):
    # ranked_players_df = retrieve_dataframe_from_sqlite("ranked_players_df")
    if sleeper_id in ranked_players_df['sleeper_id'].values:
        return ranked_players_df.loc[ranked_players_df["sleeper_id"] == str(sleeper_id), "Rating"].iloc[0]
    else:
        return 0
    
def get_total_ranking_for_list(players, ranked_players_df):
  total_ranking = sum(int(get_player_rating(player, ranked_players_df)) for player in players)
  return total_ranking

def get_players_at_position_from_roster(roster, position):
    players_df = retrieve_dataframe_from_sqlite("players_df")
    players_at_position = []
    for player_id in roster:
        if player_id in players_df.index and players_df.loc[player_id, 'position'] == position:
            players_at_position.append(player_id)
    return players_at_position

def get_players_at_position_from_owner_id(owner_id, position):
    players_df = retrieve_dataframe_from_sqlite("players_df")
    roster_df = retrieve_dataframe_from_sqlite("roster_df")
    
    players_df.set_index('player_id', inplace=True)

    owner_roster = roster_df[roster_df['owner_id'] == owner_id]
    if owner_roster.empty:
        return []
    players = owner_roster['players'].iloc[0]
    players_at_position = []
    
    for player_id in players:
        if player_id in players_df.index and players_df.loc[player_id, 'position'] == position:
            players_at_position.append(player_id)
            
    return players_at_position

def get_players_at_position_from_owners(owner_ids, position):
    data = []
    for owner_id in owner_ids:
        players = get_players_at_position_from_owner_id(owner_id, position)
        data.append({'owner_id': owner_id, 'players': players})
    df = pd.DataFrame(data)
    return df

def get_player_names_from_sleeper_ids(sleeper_ids):
    players_df = retrieve_dataframe_from_sqlite("players_df")
    player_names = []
    for sleeper_id in sleeper_ids:
        try:
            player_name = players_df[players_df['sleeper_id'] == sleeper_id]['full_name'].iloc[0]
            player_names.append(player_name)
        except IndexError:
            print(f"Warning: Player with sleeper_id '{sleeper_id}' not found.")
    return player_names
    
def get_positional_strengths():
    roster_df = retrieve_dataframe_from_sqlite("roster_df")
    league_users_df = retrieve_dataframe_from_sqlite("league_users_df")
    ranked_players_df = retrieve_dataframe_from_sqlite("ranked_players_df")
    players_df = retrieve_dataframe_from_sqlite("players_df")
    print("retrieved roster and league users dfs")
    positional_strengths_df = pd.DataFrame(roster_df['owner_id'].unique(), columns=["owner_id"])
    positional_strengths_df['display_name'] = positional_strengths_df['owner_id'].map(league_users_df.set_index('user_id')['display_name'])
    print("got display name")
    
    unique_owners = positional_strengths_df['owner_id'].unique()
    qb_rankings = {}
    for owner_id in unique_owners:
        qbs = get_players_at_position_from_owner_id(owner_id, "QB")
        qb_rankings[owner_id] = get_total_ranking_for_list(qbs, ranked_players_df)  # instant
    positional_strengths_df['qb_rating'] = positional_strengths_df['owner_id'].map(qb_rankings)
    print("computed qb ratings")

    rb_rankings = {}
    for owner_id in unique_owners:
        rbs = get_players_at_position_from_owner_id(owner_id, "RB")
        rb_rankings[owner_id] = get_total_ranking_for_list(rbs, ranked_players_df)
    positional_strengths_df['rb_rating'] = positional_strengths_df['owner_id'].map(rb_rankings)
    print("computed rb ratings")

    wr_rankings = {}
    for owner_id in unique_owners:
        wrs = get_players_at_position_from_owner_id(owner_id, "WR")
        wr_rankings[owner_id] = get_total_ranking_for_list(wrs, ranked_players_df)
    positional_strengths_df['wr_rating'] = positional_strengths_df['owner_id'].map(wr_rankings)
    print("computed wr ratings")

    te_rankings = {}
    for owner_id in unique_owners:
        tes = get_players_at_position_from_owner_id(owner_id, "TE")
        te_rankings[owner_id] = get_total_ranking_for_list(tes, ranked_players_df)
    positional_strengths_df['te_rating'] = positional_strengths_df['owner_id'].map(te_rankings)
    print("computed te ratings")

    print("got pos rankings")
    return positional_strengths_df

def is_above_median(owner_id, position):
    positional_strengths_df = retrieve_dataframe_from_sqlite("positional_strengths_df")
    position_column = position.lower() + '_rating'

    if position_column not in positional_strengths_df.columns:
        print(f"Error: Invalid position '{position}'.")
        return None

    owner_data = positional_strengths_df[positional_strengths_df['owner_id'] == owner_id]

    if owner_data.empty:
        print(f"Error: Owner with ID '{owner_id}' not found.")
        return None

    owner_rating = owner_data[position_column].iloc[0]
    median_rating = positional_strengths_df[position_column].median()

    return owner_rating > median_rating

def owner_positions_of_need(owner_id):
    positions_of_need = []
    for position in ["QB", "RB", "WR", "TE"]:
        above_median = is_above_median(owner_id, position)
        if above_median is not None:
            if not above_median:
                positions_of_need.append(position)
                
    return positions_of_need

def owner_positions_of_strength(owner_id):
    positions_of_strength = []
    for position in ["QB", "RB", "WR", "TE"]:
        above_median = is_above_median(owner_id, position)
        if above_median is not None:
            if  above_median:
                positions_of_strength.append(position)
    return positions_of_strength

def get_players_to_trade_away(owner_id):
    this_owner_positions_of_strength = owner_positions_of_strength(owner_id)
    players_to_trade_away = []
    for pos in this_owner_positions_of_strength:
        players_at_pos = get_players_at_position_from_owners([owner_id], pos)["players"]
        for player_list in players_at_pos:
            for player in player_list:
                players_to_trade_away.append(player)

    return get_player_names_from_sleeper_ids(players_to_trade_away)

def get_rosters_without_position_need(position):
    positional_strengths_df = retrieve_dataframe_from_sqlite("positional_strengths_df")
    rosters_without_need = []
    for owner_id in positional_strengths_df['owner_id']:
        if position.upper() not in owner_positions_of_need(owner_id):
            rosters_without_need.append(owner_id)
    return rosters_without_need

def generate_trade_proposals(players_to_trade_away, players_likely_to_be_traded_df):
    ranked_players_df = retrieve_dataframe_from_sqlite("ranked_players_df")
    trade_proposals = []
    tolerance = 0.05  # 5% tolerance

    for index, row in players_likely_to_be_traded_df.iterrows():
        for player_for in row['players']:
            for player_away in players_to_trade_away:
                # Find ratings for players
                try:
                    rating_for = int(ranked_players_df[ranked_players_df['Player'] == player_for]['Rating'].iloc[0])
                    rating_away = int(ranked_players_df[ranked_players_df['Player'] == player_away]['Rating'].iloc[0])

                    position_for = ranked_players_df[ranked_players_df['Player'] == player_for]['position'].iloc[0]
                    position_away = ranked_players_df[ranked_players_df['Player'] == player_away]['position'].iloc[0]

                    # Check if ratings are within tolerance
                    if abs(rating_for - rating_away) <= rating_for * tolerance :
                        trade_proposals.append([player_for, position_for, rating_for, player_away, position_away, rating_away])
                except IndexError:
                    # Handle cases where a player is not found in ranked_players_df
                    # print(f"Warning: Player '{player_for}' or '{player_away}' not found in rankings.")
                    continue

    trade_proposal_df = pd.DataFrame(
        trade_proposals,
        columns=[
            "add_player", "add_position", "add_rating",
            "send_player", "send_position", "send_rating"
        ]
    )
    return trade_proposal_df

def identify_trade_opportunities_from_owner(owner_id):
    league_users_df = retrieve_dataframe_from_sqlite("league_users_df")
    owner_positions_you_need = owner_positions_of_need(owner_id)
    owner_players_to_trade_away = get_players_to_trade_away(owner_id)
    trade_targets_df_list =[]
    for pos in owner_positions_you_need:
        trade_targets_df_list.append(get_players_at_position_from_owners(get_rosters_without_position_need(pos), pos))

    if not trade_targets_df_list: return pd.DataFrame({"message": ["You have no positional weaknesses"]})
    trade_targets_df = pd.concat(trade_targets_df_list, ignore_index=True)
    trade_targets_df["players"] = trade_targets_df["players"].apply(get_player_names_from_sleeper_ids)
    trade_targets_df["owner_name"] = trade_targets_df['owner_id'].map(league_users_df.set_index('user_id')['display_name'])
    trade_targets_df = trade_targets_df[["owner_id", "owner_name", "players"]]
    trade_targets_df = trade_targets_df.groupby(["owner_id", "owner_name"], as_index=False)["players"].sum()
    trade_proposals = generate_trade_proposals(owner_players_to_trade_away, trade_targets_df)

    return trade_proposals;

def get_owner_id_from_display_name(display_name):
    league_users_df = retrieve_dataframe_from_sqlite("league_users_df")
    # print(f"Type of league_users_df: {type(league_users_df)}")
    try:
        owner_id = league_users_df.loc[league_users_df['display_name'] == display_name, 'user_id'].iloc[0]
        return owner_id
    except IndexError:
        return None

@app.route("/")
def home():
    # return send_file("index.html")
    return send_from_directory(app.static_folder, "index.html")

# Set LeagueId API route
@app.route("/setLeagueId", methods=["POST"])
def set_league_id():
    data = json.loads(request.data)
    print("Data from trying to set league ID:", data)
    memory_storage["league_id"] = data.get("leagueId", "")
    print(memory_storage.get("league_id", 'No string found for this key'))
    print("I HAVE SET THE LEAGUE ID TO:", memory_storage.get("league_id", 'No string found for this key'))
    
    # get_all_sleeper_dfs()
    
    return {"status": "success", "leagueId": memory_storage.get("league_id", 'No string found for this key')}

# Test rankings df API route
@app.route("/getRankings")
def get_rankings():
    rankings_df = retrieve_dataframe_from_sqlite("rankings_df")
    first_rating = rankings_df['Rating'].iloc[1]   
    print("First rating: ", first_rating, rankings_df['Player'].iloc[1])
    return first_rating

# Get league users API route
@app.route("/getLeagueUsers/<league_id>")
def get_league_users_route(league_id):
    # leagueId = memory_storage.get("league_id", 'No string found for this key')
    league_users_df = get_league_users(league_id)
    print("Here is the league ID:", league_id)
    users = league_users_df[['display_name', 'avatar']].to_dict(orient='records')
    return {"users": users}

# Get trade opportunities from owner API route
@app.route("/getTradeOpportunitiesFromOwner/<league_id>/<user_name>")
def get_trade_opportunities_from_owner_route(league_id, user_name):
    print("league_id :", league_id)
    get_all_sleeper_dfs(league_id)
    owner_id = get_owner_id_from_display_name(user_name);
    trade_opportunities_df = identify_trade_opportunities_from_owner(owner_id);
    trade_opportunities_json = trade_opportunities_df.where(pd.notna(trade_opportunities_df), None).to_dict(orient="records")
    return trade_opportunities_json

# Get owner positions of strength API route
@app.route("/getOwnerPositionsOfStrength/<league_id>/<user_name>")
def get_owner_positions_of_strength_route(league_id, user_name):
    #debug
    get_all_sleeper_dfs(league_id)
    owner_id = get_owner_id_from_display_name(user_name)
    if owner_id is None:
        return {"error": "Owner not found"}
    positions_of_strength = owner_positions_of_strength(owner_id)
    return {"positions_of_strength": positions_of_strength}

# Get owner positions of weakness API route
@app.route("/getOwnerPositionsOfNeed/<league_id>/<user_name>")
def get_owner_positions_of_need_route(league_id, user_name):
    get_all_sleeper_dfs(league_id)
    owner_id = get_owner_id_from_display_name(user_name)
    if owner_id is None:
        return {"error": "Owner not found"}
    positions_of_need = owner_positions_of_need(owner_id)
    return {"positions_of_need": positions_of_need}

if __name__ == "__main__":   
    print("STARTING APP")
    app.run()