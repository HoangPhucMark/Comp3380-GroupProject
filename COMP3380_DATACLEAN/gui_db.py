import sqlite3
import sys
import os
from final_cleaner import NFLDataETL  # Add this import at the top
from tqdm import tqdm
import time

# Connect to the SQLite database
conn = sqlite3.connect('nfl_database.db')
cursor = conn.cursor()

def main_menu():
    while True:
        print("\n-------------------------NFL Database Interface Main Menu----------------------------------")
        print("1. Player")
        print("2. Team")
        print("3. Match")
        print("4. Award")
        print("5. Delete All Data")
        print("6. Repopulate Database")  # New option
        print("7. Exit")
        print("--------------------------------------------------------------------------------------------")
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == '1':
            player_menu()
        elif choice == '2':
            team_menu()
        elif choice == '3':
            match_menu()
        elif choice == '4':
            award_menu()
        elif choice == '5':
            delete_all_data()
        elif choice == '6':
            repopulate_database()
        elif choice == '7':
            print("Exiting the interface. Goodbye!")
            conn.close()
            sys.exit()
        else:
            print_invalid_input()

def player_menu():
    while True:
        print("\n---------------------NFL Database Interface Player Menu------------------------------------")
        print("a. Search for a player's name")
        print("b. Return BMI of a player")
        print("c. Display awards of a player")
        print("d. Display all players")
        print("e. Return top players with most tackles")
        print("f. Return to main menu")
        print("--------------------------------------------------------------------------------------------")
        choice = input("Enter your choice (a-f): ").strip().lower()
        if choice == 'a':
            search_player_by_name()
        elif choice == 'b':
            get_player_bmi()
        elif choice == 'c':
            display_player_awards()
        elif choice == 'd':
            display_all_players()
        elif choice == 'e':
            top_players_most_tackles()
        elif choice == 'f':
            break
        else:
            print_invalid_input()

def team_menu():
    while True:
        print("\n----------------------NFL Database Interface Team Menu--------------------------------------")
        print("a. Display all teams")
        print("b. Search for all players from a specific team")
        print("c. Display the team with the most awards")
        print("d. Search for awards won by players from a specific team")
        print("e. Return to main menu")
        print("--------------------------------------------------------------------------------------------")
        choice = input("Enter your choice (a-e): ").strip().lower()
        if choice == 'a':
            display_all_teams()
        elif choice == 'b':
            search_players_by_team()
        elif choice == 'c':
            team_with_most_awards()
        elif choice == 'd':
            awards_by_team_players()
        elif choice == 'e':
            break
        else:
            print_invalid_input()

def match_menu():
    while True:
        print("\n---------------------NFL Database Interface Match Menu--------------------------------------")
        print("a. Search participated teams for a known game")
        print("b. List plays that happened during a specific game")
        print("c. Find games with no tackles")
        print("d. Return to main menu")
        print("--------------------------------------------------------------------------------------------")
        choice = input("Enter your choice (a-d): ").strip().lower()
        if choice == 'a':
            search_teams_by_game()
        elif choice == 'b':
            list_plays_in_game()
        elif choice == 'c':
            games_with_no_tackles()
        elif choice == 'd':
            break
        else:
            print_invalid_input()

# Update the award_menu function to include the statistics option
def award_menu():
    while True:
        print("\n---------------------NFL Database Interface Award Menu--------------------------------------")
        print("a. List all nominees")
        print("b. Search nominees for a specific award")
        print("c. View award statistics")
        print("d. Return to main menu")
        print("--------------------------------------------------------------------------------------------")
        choice = input("Enter your choice (a-d): ").strip().lower()
        
        if choice == 'a':
            list_all_nominees()
        elif choice == 'b':
            search_nominees_for_award()
        elif choice == 'c':
            award_statistics_menu()
        elif choice == 'd':
            break
        else:
            print_invalid_input()


def delete_all_data():
    """Delete all data from the database with progress bars"""
    print("\nDelete All Data")
    print("--------------")
    
    # Confirm with user
    confirm = input("\nWARNING: This will delete ALL data from the database. Are you sure? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Deletion cancelled.")
        input("\nPress Enter to return to the main menu...")
        return
    
    try:
        # Get list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # Setup progress bar for overall process
        print("\nDeleting data from all tables...")
        with tqdm(total=len(tables), desc="Overall Progress") as pbar:
            for table in tables:
                table_name = table[0]
                
                # Get count of records in table
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_count = cursor.fetchone()[0]
                
                # Show deletion progress for each table
                print(f"\nDeleting {record_count} records from {table_name}...")
                
                # If table has many records, delete in batches with progress bar
                if record_count > 1000:
                    batch_size = 1000
                    deleted = 0
                    with tqdm(total=record_count, desc=f"Deleting from {table_name}") as t_pbar:
                        while deleted < record_count:
                            cursor.execute(f"DELETE FROM {table_name} LIMIT {batch_size}")
                            deleted += cursor.rowcount
                            t_pbar.update(min(batch_size, record_count - (deleted - batch_size)))
                            conn.commit()
                else:
                    # For small tables, delete all at once
                    cursor.execute(f"DELETE FROM {table_name}")
                    conn.commit()
                
                # Show completion for this table
                time.sleep(0.1)  # Small delay for visual feedback
                pbar.update(1)
        
        print("\nAll data has been successfully deleted!")
        print("\nSummary of deleted data:")
        print("-" * 40)
        for table in tables:
            print(f"{table[0]:<20} Records deleted")
        
    except Exception as e:
        print(f"\nError during deletion: {str(e)}")
        print("The database may be in an inconsistent state.")
        conn.rollback()
    
    input("\nPress Enter to return to the main menu...")


def print_invalid_input():
    print("\n-------------------------------- Error: Invalid Input --------------------------------------------")
    print("The input provided is not valid. Please check your input and try again.")
    print("Press Enter to return to the previous menu.")
    input()

# Player menu functions
def search_player_by_name():
    name = input("Enter the player's name (or part of name): ").strip()
    if not name:
        print("Name cannot be empty.")
        input("Press Enter to return to the previous menu.")
        return

    player = get_player_selection(name)
    if player:
        cursor.execute("""
            SELECT p.nflId, p.displayName, p.position, p.height, p.weight, c.collegeName
            FROM Player p
            LEFT JOIN College c ON p.collegeId = c.collegeId
            WHERE p.nflId = ?
        """, (player[0],))
        player_details = cursor.fetchone()
        
        print("\nPlayer Details:")
        print(f"Name: {player_details[1]}")
        print(f"Position: {player_details[2]}")
        print(f"Height: {player_details[3]}")
        print(f"Weight: {player_details[4]} lbs")
        print(f"College: {player_details[5] if player_details[5] else 'Not available'}")
    else:
        print("No player found with that name.")
    input("Press Enter to return to the previous menu.")

def get_player_bmi():
    name = input("Enter the player's name (or part of name): ").strip()
    if not name:
        print("Name cannot be empty.")
        input("Press Enter to return to the previous menu.")
        return

    player = get_player_selection(name)
    if player:
        cursor.execute("SELECT weight, height FROM Player WHERE nflId = ?", (player[0],))
        player_data = cursor.fetchone()
        
        try:
            weight = float(player_data[0])
            height_str = player_data[1]
            
            # Parse height in format "6-2"
            feet, inches = map(int, height_str.split('-'))
            height_inches = (feet * 12 + inches)
            
            # Calculate BMI
            bmi = (weight / (height_inches ** 2)) * 703
            
            print(f"\nBMI Calculation for {player[1]}:")
            print(f"Height: {height_str} ({height_inches} inches)")
            print(f"Weight: {weight} lbs")
            print(f"BMI: {bmi:.2f}")
            
            # Add BMI category
            if bmi < 18.5:
                category = "Underweight"
            elif bmi < 25:
                category = "Normal weight"
            elif bmi < 30:
                category = "Overweight"
            else:
                category = "Obese"
            print(f"Category: {category}")
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            print(f"Error calculating BMI: Invalid data format")
    else:
        print("No player found with that name.")
    input("Press Enter to return to the previous menu.")

def display_player_awards():
    name = input("Enter the player's name (or part of name): ").strip()
    if not name:
        print("Name cannot be empty.")
        input("Press Enter to return to the previous menu.")
        return

    player = get_player_selection(name)
    if player:
        cursor.execute("""
            SELECT DISTINCT a.awardName 
            FROM Awards a
            JOIN Nominees n ON a.awardId = n.awardId
            WHERE n.nflId = ?
        """, (player[0],))
        awards = cursor.fetchall()
        
        print(f"\nAwards for {player[1]}:")
        if awards:
            for idx, award in enumerate(awards, 1):
                print(f"{idx}. {award[0]}")
        else:
            print("No awards found for this player.")
    else:
        print("No player found with that name.")
    input("Press Enter to return to the previous menu.")


def display_all_players():
    cursor.execute("SELECT nflId, displayName, position FROM Player")
    players = cursor.fetchall()
    print("\nList of all players:")
    for player in players:
        print(f"ID: {player[0]}, Name: {player[1]}, Position: {player[2]}")
    input("Press Enter to return to the previous menu.")

def top_players_most_tackles():
    cursor.execute("""
        SELECT p.displayName, p.nflId, COUNT(t.tackle) as tackle_count
        FROM Player p
        JOIN Tackles t ON p.nflId = t.nflId
        WHERE t.tackle = 1
        GROUP BY p.nflId
        ORDER BY tackle_count DESC
        LIMIT 5
    """)
    players = cursor.fetchall()
    if players:
        print("\n--------------------- Top Players with Most Tackles ------------------------")
        print(f"{'Player Name':<20} {'NFL ID':<10} {'Tackles Count':<15}")
        for player in players:
            print(f"{player[0]:<20} {player[1]:<10} {player[2]:<15}")
    else:
        print("No tackle data available.")
    input("Press Enter to return to the previous menu.")

# Team menu functions
def display_all_teams():
    cursor.execute("SELECT teamAbbreviation, teamName FROM Team")
    teams = cursor.fetchall()
    print("\nList of all teams:")
    for team in teams:
        print(f"{team[0]} - {team[1]}")
    input("Press Enter to return to the previous menu.")

def search_players_by_team():
    cursor.execute("SELECT DISTINCT teamAbbreviation, teamName FROM Team ORDER BY teamName")
    teams = cursor.fetchall()
    
    print("\nAvailable teams:")
    for idx, team in enumerate(teams, 1):
        print(f"{idx}. {team[1]} ({team[0]})")
    
    while True:
        try:
            choice = input("\nEnter team number (or 0 to cancel): ").strip()
            if choice == '0':
                return
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(teams):
                selected_team = teams[choice_idx]
                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

    cursor.execute("""
        SELECT DISTINCT p.displayName, p.position, p.height, p.weight
        FROM Player p
        JOIN Play pl ON p.nflId = pl.ballCarrierId
        JOIN Game g ON pl.gameId = g.gameId
        WHERE g.homeTeam = ? OR g.visitorTeam = ?
        ORDER BY p.position, p.displayName
    """, (selected_team[0], selected_team[0]))
    
    players = cursor.fetchall()
    if players:
        print(f"\nPlayers from {selected_team[1]}:")
        current_position = None
        for player in players:
            if player[1] != current_position:
                current_position = player[1]
                print(f"\n{current_position}s:")
            print(f"- {player[0]} ({player[2]}, {player[3]} lbs)")
    else:
        print(f"No players found for {selected_team[1]}")
    input("Press Enter to return to the previous menu.")


def team_with_most_awards():
    cursor.execute("""
        SELECT g.homeTeam, COUNT(n.awardId) as award_count
        FROM Game g
        JOIN Play p ON g.gameId = p.gameId
        JOIN Player pl ON p.ballCarrierId = pl.nflId
        JOIN Nominees n ON pl.nflId = n.nflId
        GROUP BY g.homeTeam
        ORDER BY award_count DESC
        LIMIT 1
    """)
    team = cursor.fetchone()
    if team:
        print(f"\nTeam with the most awards: {team[0]} ({team[1]} awards)")
    else:
        print("No award data available.")
    input("Press Enter to return to the previous menu.")


def awards_by_team_players():
    team_abbr = input("Enter the team abbreviation: ").strip().upper()
    cursor.execute("""
        SELECT p.displayName, a.awardName, a.season
        FROM Player p
        JOIN AwardWinner aw ON p.nflId = aw.playerId
        JOIN Award a ON aw.awardId = a.awardId
        WHERE aw.teamAbbreviation = ?
    """, (team_abbr,))
    awards = cursor.fetchall()
    if awards:
        print(f"\nAwards won by players from {team_abbr}:")
        for award in awards:
            print(f"Player: {award[0]}, Award: {award[1]}, Season: {award[2]}")
    else:
        print(f"No awards found for team {team_abbr}.")
    input("Press Enter to return to the previous menu.")

# Match menu functions
def search_teams_by_game():
    game_id = input("Enter the Game ID: ").strip()
    cursor.execute("SELECT homeTeam, visitorTeam FROM Game WHERE gameId = ?", (game_id,))
    game = cursor.fetchone()
    if game:
        print(f"\nTeams participated in game {game_id}:")
        print(f"Home Team: {game[0]}")
        print(f"Visitor Team: {game[1]}")
    else:
        print("No game found with that ID.")
    input("Press Enter to return to the previous menu.")

def list_plays_in_game():
    game_id = input("Enter the Game ID: ").strip()
    cursor.execute("""
        SELECT playId, possessionTeam, playResult
        FROM Play
        WHERE gameId = ?
    """, (game_id,))
    plays = cursor.fetchall()
    if plays:
        print(f"\nPlays in game {game_id}:")
        for play in plays:
            print(f"Play ID: {play[0]}, Team: {play[1]}, Result: {play[2]}")
    else:
        print("No plays found for that game.")
    input("Press Enter to return to the previous menu.")

def games_with_no_tackles():
    cursor.execute("""
        SELECT g.gameId, g.homeTeam, g.visitorTeam
        FROM Game g
        WHERE NOT EXISTS (
            SELECT 1 FROM Tackles t WHERE t.gameId = g.gameId AND t.tackle = 1
        )
    """)
    games = cursor.fetchall()
    if games:
        print("\nGames with no tackles:")
        for game in games:
            print(f"Game ID: {game[0]}, Teams: {game[1]} vs {game[2]}")
    else:
        print("All games have tackles recorded.")
    input("Press Enter to return to the previous menu.")

# Award menu functions
def list_all_nominees():
    """Improved function to list all nominees with filtering options"""
    while True:
        print("\nList All Nominees")
        print("----------------")
        print("1. Show all nominees")
        print("2. Filter by position")
        print("3. Filter by award")
        print("0. Return to previous menu")
        
        choice = input("\nYour choice (0-3): ").strip()
        
        if choice == '0':
            break
            
        elif choice == '1':
            cursor.execute("""
                SELECT DISTINCT
                    p.displayName,
                    p.position,
                    a.awardName,
                    t.teamName
                FROM Nominees n
                JOIN Player p ON n.nflId = p.nflId
                JOIN Awards a ON n.awardId = a.awardId
                LEFT JOIN (
                    SELECT DISTINCT ballCarrierId, homeTeam
                    FROM Play pl
                    JOIN Game g ON pl.gameId = g.gameId
                    GROUP BY ballCarrierId
                ) as player_team ON p.nflId = player_team.ballCarrierId
                LEFT JOIN Team t ON player_team.homeTeam = t.teamAbbreviation
                ORDER BY p.displayName, a.awardName
            """)
            
        elif choice == '2':
            cursor.execute("SELECT DISTINCT position FROM Player ORDER BY position")
            positions = cursor.fetchall()
            
            print("\nAvailable positions:")
            for idx, pos in enumerate(positions, 1):
                print(f"{idx}. {pos[0]}")
                
            try:
                pos_choice = input("\nEnter position number (0 to cancel): ").strip()
                if pos_choice == '0':
                    continue
                pos_idx = int(pos_choice) - 1
                if 0 <= pos_idx < len(positions):
                    selected_position = positions[pos_idx][0]
                    cursor.execute("""
                        SELECT DISTINCT
                            p.displayName,
                            p.position,
                            a.awardName,
                            t.teamName
                        FROM Nominees n
                        JOIN Player p ON n.nflId = p.nflId
                        JOIN Awards a ON n.awardId = a.awardId
                        LEFT JOIN (
                            SELECT DISTINCT ballCarrierId, homeTeam
                            FROM Play pl
                            JOIN Game g ON pl.gameId = g.gameId
                            GROUP BY ballCarrierId
                        ) as player_team ON p.nflId = player_team.ballCarrierId
                        LEFT JOIN Team t ON player_team.homeTeam = t.teamAbbreviation
                        WHERE p.position = ?
                        ORDER BY p.displayName, a.awardName
                    """, (selected_position,))
                else:
                    print("Invalid position number.")
                    continue
            except ValueError:
                print("Please enter a valid number.")
                continue
                
        elif choice == '3':
            selected_award = get_award_selection()
            if not selected_award:
                continue
                
            cursor.execute("""
                SELECT DISTINCT
                    p.displayName,
                    p.position,
                    a.awardName,
                    t.teamName
                FROM Nominees n
                JOIN Player p ON n.nflId = p.nflId
                JOIN Awards a ON n.awardId = a.awardId
                LEFT JOIN (
                    SELECT DISTINCT ballCarrierId, homeTeam
                    FROM Play pl
                    JOIN Game g ON pl.gameId = g.gameId
                    GROUP BY ballCarrierId
                ) as player_team ON p.nflId = player_team.ballCarrierId
                LEFT JOIN Team t ON player_team.homeTeam = t.teamAbbreviation
                WHERE n.awardId = ?
                ORDER BY p.displayName
            """, (selected_award[0],))
            
        else:
            print("Invalid choice. Please try again.")
            continue
            
        nominees = cursor.fetchall()
        if nominees:
            print("\n" + "-" * 80)
            print(f"{'Player Name':<30} {'Position':<10} {'Award':<25} {'Team':<15}")
            print("-" * 80)
            
            for nominee in nominees:
                team_name = nominee[3] if nominee[3] else 'Not Available'
                print(f"{nominee[0]:<30} {nominee[1]:<10} {nominee[2]:<25} {team_name:<15}")
            
            print(f"\nTotal unique nominees: {len(nominees)}")
        else:
            print("\nNo nominees found matching the criteria.")
            
        input("\nPress Enter to continue...")



def search_nominees_for_award():
    """Improved function to search nominees for a specific award"""
    print("\nSearch Award Nominees")
    print("--------------------")
    
    selected_award = get_award_selection()
    if not selected_award:
        print("Award selection cancelled.")
        input("\nPress Enter to return to the previous menu.")
        return

    cursor.execute("""
        SELECT DISTINCT
            p.displayName,
            p.position,
            t.teamName
        FROM Nominees n
        JOIN Player p ON n.nflId = p.nflId
        JOIN Awards a ON n.awardId = a.awardId
        LEFT JOIN (
            SELECT DISTINCT ballCarrierId, homeTeam
            FROM Play pl
            JOIN Game g ON pl.gameId = g.gameId
            GROUP BY ballCarrierId
        ) as player_team ON p.nflId = player_team.ballCarrierId
        LEFT JOIN Team t ON player_team.homeTeam = t.teamAbbreviation
        WHERE n.awardId = ?
        ORDER BY p.displayName
    """, (selected_award[0],))
    
    nominees = cursor.fetchall()
    
    if nominees:
        print(f"\nNominees for {selected_award[1]}:")
        print("-" * (20 + len(selected_award[1])))
        print(f"{'Player Name':<30} {'Position':<10} {'Team':<20}")
        print("-" * 60)
        
        for nominee in nominees:
            team_name = nominee[2] if nominee[2] else 'Not Available'
            print(f"{nominee[0]:<30} {nominee[1]:<10} {team_name:<20}")
        
        print(f"\nTotal unique nominees: {len(nominees)}")
        
        positions = {}
        for nominee in nominees:
            positions[nominee[1]] = positions.get(nominee[1], 0) + 1
        
        print("\nNominees by position:")
        for pos, count in sorted(positions.items()):
            print(f"{pos}: {count}")
            
    else:
        print(f"\nNo nominees found for {selected_award[1]}")
    
    input("\nPress Enter to return to the previous menu.")


def award_statistics_menu():
    while True:
        print("\n----------------------Award Statistics Menu--------------------------------")
        print("1. Most awards by position")
        print("2. Top 5 players with most nominations")
        print("3. Awards distribution by team")
        print("4. Position diversity in awards")
        print("5. Year-over-year award trends")
        print("0. Return to previous menu")
        print("------------------------------------------------------------------------")
        
        choice = input("Enter your choice (0-5): ").strip()
        
        if choice == '0':
            break
            
        elif choice == '1':
            show_awards_by_position()
        elif choice == '2':
            show_top_nominees()
        elif choice == '3':
            show_awards_by_team()
        elif choice == '4':
            show_position_diversity()
        elif choice == '5':
            show_award_trends()
        else:
            print("Invalid choice. Please try again.")

def show_awards_by_position():
    print("\nAwards Won by Position")
    print("---------------------")
    
    cursor.execute("""
        SELECT 
            p.position,
            COUNT(DISTINCT n.nflId) as player_count,
            COUNT(*) as nomination_count,
            GROUP_CONCAT(DISTINCT p.displayName) as players
        FROM Nominees n
        JOIN Player p ON n.nflId = p.nflId
        GROUP BY p.position
        ORDER BY nomination_count DESC
    """)
    
    results = cursor.fetchall()
    if results:
        print(f"{'Position':<10} {'Players':<10} {'Nominations':<12}")
        print("-" * 50)
        for row in results:
            print(f"{row[0]:<10} {row[1]:<10} {row[2]:<12}")
            print(f"Notable players: {row[3][:100]}...")
            print("-" * 50)
    else:
        print("No award data available.")

def show_top_nominees():
    print("\nTop 5 Players with Most Nominations")
    print("----------------------------------")
    
    cursor.execute("""
        SELECT 
            p.displayName,
            p.position,
            COUNT(*) as nom_count,
            GROUP_CONCAT(DISTINCT a.awardName) as awards
        FROM Nominees n
        JOIN Player p ON n.nflId = p.nflId
        JOIN Awards a ON n.awardId = a.awardId
        GROUP BY n.nflId
        ORDER BY nom_count DESC
        LIMIT 5
    """)
    
    results = cursor.fetchall()
    if results:
        for idx, row in enumerate(results, 1):
            print(f"\n{idx}. {row[0]} ({row[1]})")
            print(f"   Total nominations: {row[2]}")
            print(f"   Nominated for: {row[3]}")
    else:
        print("No nomination data available.")

def show_awards_by_team():
    print("\nAwards Distribution by Team")
    print("-------------------------")
    
    cursor.execute("""
        WITH PlayerTeams AS (
            SELECT DISTINCT 
                p.nflId,
                g.homeTeam as team
            FROM Player p
            JOIN Play pl ON p.nflId = pl.ballCarrierId
            JOIN Game g ON pl.gameId = g.gameId
        )
        SELECT 
            t.teamName,
            COUNT(DISTINCT n.nflId) as player_count,
            COUNT(*) as award_count
        FROM PlayerTeams pt
        JOIN Team t ON pt.team = t.teamAbbreviation
        JOIN Nominees n ON pt.nflId = n.nflId
        GROUP BY t.teamName
        ORDER BY award_count DESC
    """)
    
    results = cursor.fetchall()
    if results:
        print(f"{'Team':<25} {'Players':<10} {'Nominations':<12}")
        print("-" * 47)
        for row in results:
            print(f"{row[0]:<25} {row[1]:<10} {row[2]:<12}")
    else:
        print("No team award data available.")

def show_position_diversity():
    print("\nPosition Diversity in Awards")
    print("---------------------------")
    
    cursor.execute("""
        SELECT 
            a.awardName,
            COUNT(DISTINCT p.position) as position_count,
            GROUP_CONCAT(DISTINCT p.position) as positions
        FROM Awards a
        JOIN Nominees n ON a.awardId = n.awardId
        JOIN Player p ON n.nflId = p.nflId
        GROUP BY a.awardName
        ORDER BY position_count DESC
    """)
    
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"\n{row[0]}")
            print(f"Number of different positions nominated: {row[1]}")
            print(f"Positions: {row[2]}")
            print("-" * 50)
    else:
        print("No position diversity data available.")

def show_award_trends():
    print("\nYear-over-Year Award Trends")
    print("--------------------------")
    
    # This query assumes you have a year or season field in your Awards table
    # Modify according to your actual schema
    cursor.execute("""
        SELECT 
            a.awardName,
            COUNT(DISTINCT n.nflId) as unique_nominees,
            COUNT(*) as total_nominations
        FROM Awards a
        JOIN Nominees n ON a.awardId = n.awardId
        GROUP BY a.awardName
        ORDER BY total_nominations DESC
    """)
    
    results = cursor.fetchall()
    if results:
        print(f"{'Award Name':<40} {'Unique Nominees':<15} {'Total Nominations':<15}")
        print("-" * 70)
        for row in results:
            print(f"{row[0]:<40} {row[1]:<15} {row[2]:<15}")
    else:
        print("No trend data available.")

    
    """ HELPER FUNCTIONS """
def get_player_selection(name_query):
    """Helper function to get player selection from a partial name match"""
    cursor.execute("SELECT nflId, displayName, position FROM Player WHERE displayName LIKE ?", ('%' + name_query + '%',))
    players = cursor.fetchall()
    
    if not players:
        return None
    
    if len(players) == 1:
        return players[0]
    
    print("\nMultiple players found. Please select one:")
    for idx, player in enumerate(players, 1):
        print(f"{idx}. {player[1]} ({player[2]})")
    
    while True:
        try:
            choice = input("\nEnter the number of your selection (or 0 to cancel): ").strip()
            if choice == '0':
                return None
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(players):
                return players[choice_idx]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
            
def list_all_awards():
    """Helper function to get and display all available awards"""
    cursor.execute("SELECT DISTINCT awardId, awardName FROM Awards ORDER BY awardName")
    awards = cursor.fetchall()
    
    if not awards:
        print("No awards found in the database.")
        return None
    
    print("\nAvailable Awards:")
    print("------------------")
    for idx, award in enumerate(awards, 1):
        print(f"{idx}. {award[1]}")
    
    return awards

def get_award_selection():
    """Helper function to handle award selection"""
    awards = list_all_awards()
    if not awards:
        return None
    
    while True:
        print("\nSelect an award by:")
        print("1. Entering the number")
        print("2. Typing part of the award name")
        print("0. Cancel")
        
        choice = input("\nYour choice (0-2): ").strip()
        
        if choice == '0':
            return None
        
        elif choice == '1':
            while True:
                try:
                    num = input("\nEnter award number (0 to cancel): ").strip()
                    if num == '0':
                        return None
                    idx = int(num) - 1
                    if 0 <= idx < len(awards):
                        return awards[idx]
                    else:
                        print("Invalid number. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
        
        elif choice == '2':
            while True:
                search_term = input("\nEnter part of award name (empty to cancel): ").strip()
                if not search_term:
                    return None
                
                matching_awards = [award for award in awards 
                                 if search_term.lower() in award[1].lower()]
                
                if not matching_awards:
                    print("No awards match your search. Try again.")
                    continue
                
                print("\nMatching awards:")
                for idx, award in enumerate(matching_awards, 1):
                    print(f"{idx}. {award[1]}")
                
                try:
                    num = input("\nEnter award number (0 to cancel): ").strip()
                    if num == '0':
                        continue
                    idx = int(num) - 1
                    if 0 <= idx < len(matching_awards):
                        return matching_awards[idx]
                    else:
                        print("Invalid number. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
        
        else:
            print("Invalid choice. Please try again.")

def check_data_files():
    """Check if required data files exist"""
    required_files = [
        'big_data/games.csv',
        'big_data/players.csv',
        'big_data/plays.csv',
        'big_data/tackles.csv',
        'big_data/nominees.csv'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    return len(missing_files) == 0, missing_files

def repopulate_database():
    """Function to repopulate the database"""
    print("\nDatabase Repopulation")
    print("--------------------")
    
    # Check if data files exist
    files_exist, missing_files = check_data_files()
    if not files_exist:
        print("Error: Missing required data files:")
        for file in missing_files:
            print(f"- {file}")
        print("\nPlease ensure all required files are in the 'big_data' directory.")
        input("\nPress Enter to return to the main menu...")
        return
    
    # Confirm with user
    print("\nWARNING: This will delete all existing data and repopulate the database.")
    print("This process may take several minutes.")
    confirm = input("\nDo you want to continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Database repopulation cancelled.")
        input("\nPress Enter to return to the main menu...")
        return
    
    try:
        print("\nStarting database repopulation...")
        print("This may take several minutes. Please wait...")
        
        # Create and run ETL process
        etl = NFLDataETL()
        etl.process_all(
            games_path='big_data/games.csv',
            players_path='big_data/players.csv',
            plays_path='big_data/plays.csv',
            tackles_path='big_data/tackles.csv',
            nominees_path='big_data/nominees.csv'
        )
        
        print("\nDatabase repopulation completed successfully!")
        print("\nSummary of imported data:")
        
        # Connect to get counts
        conn = sqlite3.connect('nfl_database.db')
        cursor = conn.cursor()
        
        tables = {
            'Games': 'Game',
            'Teams': 'Team',
            'Players': 'Player',
            'Plays': 'Play',
            'Tackles': 'Tackles',
            'Awards': 'Awards',
            'Nominees': 'Nominees'
        }
        
        print("\nTable Counts:")
        print("-" * 40)
        for display_name, table_name in tables.items():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"{display_name:<20} {count:>10}")
        
        conn.close()
        
    except Exception as e:
        print(f"\nError during database repopulation: {str(e)}")
        print("The database may be in an inconsistent state.")
    
    input("\nPress Enter to return to the main menu...")



# Start the program
if __name__ == "__main__":
    main_menu()
