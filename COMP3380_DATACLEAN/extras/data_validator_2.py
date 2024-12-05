import pandas as pd
import sqlite3
import logging
from datetime import datetime
import sys
from pathlib import Path

class NFLDatabaseValidator:
    def __init__(self, db_path: str, csv_directory: str):
        self.db_path = db_path
        self.csv_directory = Path(csv_directory)
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('nfl_validation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect_db(self):
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            self.logger.error(f"Database connection error: {e}")
            raise

    def validate_games_table(self, conn: sqlite3.Connection):
        try:
            # Load CSV
            games_df = pd.read_csv(self.csv_directory / 'games.csv')
            cursor = conn.cursor()

            # Check column mapping
            csv_columns = set(games_df.columns)
            expected_columns = {
                'gameId', 'season', 'week', 'gameDate', 'gameTimeEastern',
                'homeTeamAbbr', 'visitorTeamAbbr', 'homeFinalScore', 'visitorFinalScore'
            }
            missing_columns = expected_columns - csv_columns
            if missing_columns:
                self.logger.error(f"Missing columns in games.csv: {missing_columns}")

            # Validate scores range
            invalid_scores = games_df[
                (games_df['homeFinalScore'] < 0) | 
                (games_df['visitorFinalScore'] < 0) |
                (games_df['homeFinalScore'] > 100) |
                (games_df['visitorFinalScore'] > 100)
            ]
            if not invalid_scores.empty:
                self.logger.error(f"Invalid scores found in {len(invalid_scores)} games")

            # Validate team abbreviations against Team table
            cursor.execute("SELECT teamAbbreviation FROM Team")
            valid_teams = {row[0] for row in cursor.fetchall()}
            invalid_home_teams = games_df[~games_df['homeTeamAbbr'].isin(valid_teams)]
            invalid_visitor_teams = games_df[~games_df['visitorTeamAbbr'].isin(valid_teams)]
            
            if not invalid_home_teams.empty:
                self.logger.error(f"Invalid home teams found: {invalid_home_teams['homeTeamAbbr'].unique()}")
            if not invalid_visitor_teams.empty:
                self.logger.error(f"Invalid visitor teams found: {invalid_visitor_teams['visitorTeamAbbr'].unique()}")

        except Exception as e:
            self.logger.error(f"Error validating games table: {e}")
            raise

    def validate_players_table(self, conn: sqlite3.Connection):
        try:
            players_df = pd.read_csv(self.csv_directory / 'players.csv')
            cursor = conn.cursor()

            # Validate height format (expecting format like "6-2")
            invalid_height = players_df[~players_df['height'].str.match(r'^\d-\d{1,2}$', na=True)]
            if not invalid_height.empty:
                self.logger.error(f"Invalid height format found for {len(invalid_height)} players")

            # Validate weight range (reasonable NFL player weights)
            invalid_weight = players_df[
                (players_df['weight'] < 150) | 
                (players_df['weight'] > 400)
            ]
            if not invalid_weight.empty:
                self.logger.error(f"Suspicious weight values found for {len(invalid_weight)} players")

            # Validate birth dates
            players_df['birthDate'] = pd.to_datetime(players_df['birthDate'], errors='coerce')
            invalid_dates = players_df[
                (players_df['birthDate'].dt.year < 1960) | 
                (players_df['birthDate'].dt.year > 2005)
            ]
            if not invalid_dates.empty:
                self.logger.error(f"Suspicious birth dates found for {len(invalid_dates)} players")

            # Validate positions
            valid_positions = {'QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'DB', 'K', 'P'}
            invalid_positions = players_df[~players_df['position'].isin(valid_positions)]
            if not invalid_positions.empty:
                self.logger.error(f"Invalid positions found: {invalid_positions['position'].unique()}")

        except Exception as e:
            self.logger.error(f"Error validating players table: {e}")
            raise

    def validate_plays_table(self, conn: sqlite3.Connection):
        try:
            plays_df = pd.read_csv(self.csv_directory / 'plays.csv')
            cursor = conn.cursor()

            # Validate quarter values
            invalid_quarters = plays_df[
                (plays_df['quarter'] < 1) | 
                (plays_df['quarter'] > 5)
            ]
            if not invalid_quarters.empty:
                self.logger.error(f"Invalid quarter values found in {len(invalid_quarters)} plays")

            # Validate downs
            invalid_downs = plays_df[
                (plays_df['down'] < 1) | 
                (plays_df['down'] > 4)
            ]
            if not invalid_downs.empty:
                self.logger.error(f"Invalid down values found in {len(invalid_downs)} plays")

            # Validate yards to go
            invalid_yards = plays_df[
                (plays_df['yardsToGo'] < 0) | 
                (plays_df['yardsToGo'] > 100)
            ]
            if not invalid_yards.empty:
                self.logger.error(f"Invalid yardsToGo values found in {len(invalid_yards)} plays")

            # Validate pass probability
            invalid_prob = plays_df[
                (plays_df['passProbability'] < 0) | 
                (plays_df['passProbability'] > 1)
            ]
            if not invalid_prob.empty:
                self.logger.error(f"Invalid pass probability values found in {len(invalid_prob)} plays")

        except Exception as e:
            self.logger.error(f"Error validating plays table: {e}")
            raise

    def validate_tackles_table(self, conn: sqlite3.Connection):
        try:
            tackles_df = pd.read_csv(self.csv_directory / 'tackles.csv')
            cursor = conn.cursor()

            # Validate binary columns
            binary_columns = ['tackle', 'assist', 'forcedFumble', 'pff_missedTackle']
            for col in binary_columns:
                invalid_values = tackles_df[~tackles_df[col].isin([0, 1])]
                if not invalid_values.empty:
                    self.logger.error(f"Invalid {col} values found in {len(invalid_values)} records")

            # Validate player IDs exist in Player table
            cursor.execute("SELECT DISTINCT nflId FROM Player")
            valid_players = {row[0] for row in cursor.fetchall()}
            invalid_players = tackles_df[~tackles_df['nflId'].isin(valid_players)]
            if not invalid_players.empty:
                self.logger.error(f"Invalid player IDs found in tackles: {len(invalid_players)} records")

            # Validate play references
            cursor.execute("SELECT DISTINCT gameId, playId FROM Play")
            valid_plays = {(row[0], row[1]) for row in cursor.fetchall()}
            tackles_plays = set(zip(tackles_df['gameId'], tackles_df['playId']))
            invalid_plays = tackles_plays - valid_plays
            if invalid_plays:
                self.logger.error(f"Invalid game/play combinations found in tackles: {len(invalid_plays)} records")

        except Exception as e:
            self.logger.error(f"Error validating tackles table: {e}")
            raise

    def validate_referential_integrity(self, conn: sqlite3.Connection):
        try:
            cursor = conn.cursor()

            # Check Play -> Game references
            cursor.execute("""
                SELECT COUNT(*) FROM Play p 
                LEFT JOIN Game g ON p.gameId = g.gameId 
                WHERE g.gameId IS NULL
            """)
            invalid_game_refs = cursor.fetchone()[0]
            if invalid_game_refs > 0:
                self.logger.error(f"Found {invalid_game_refs} plays referencing non-existent games")

            # Check Tackles -> Play references
            cursor.execute("""
                SELECT COUNT(*) FROM Tackles t 
                LEFT JOIN Play p ON t.gameId = p.gameId AND t.playId = p.playId 
                WHERE p.playId IS NULL
            """)
            invalid_play_refs = cursor.fetchone()[0]
            if invalid_play_refs > 0:
                self.logger.error(f"Found {invalid_play_refs} tackles referencing non-existent plays")

            # Check Player -> College references
            cursor.execute("""
                SELECT COUNT(*) FROM Player p 
                LEFT JOIN College c ON p.collegeId = c.collegeId 
                WHERE p.collegeId IS NOT NULL AND c.collegeId IS NULL
            """)
            invalid_college_refs = cursor.fetchone()[0]
            if invalid_college_refs > 0:
                self.logger.error(f"Found {invalid_college_refs} players referencing non-existent colleges")

        except Exception as e:
            self.logger.error(f"Error validating referential integrity: {e}")
            raise

    def run_validation(self):
        try:
            conn = self.connect_db()
            self.logger.info("Starting NFL database validation...")
            
            self.validate_games_table(conn)
            self.validate_players_table(conn)
            self.validate_plays_table(conn)
            self.validate_tackles_table(conn)
            self.validate_referential_integrity(conn)
            
            self.logger.info("NFL database validation completed.")
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            raise
        finally:
            if conn:
                conn.close()

def main():
    validator = NFLDatabaseValidator(
        db_path="nfl_database.db",
        csv_directory="./big_data"
    )
    validator.run_validation()

if __name__ == "__main__":
    main()
