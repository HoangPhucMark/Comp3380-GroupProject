import pandas as pd
import sqlite3
import numpy as np
from tqdm import tqdm
import logging
from datetime import datetime
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=f'nfl_etl_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
)

class NFLDataETL:
    def __init__(self, db_name='nfl_database.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        
    def connect_db(self):
        """Establish database connection"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            logging.info("Database connection established successfully")
        except Exception as e:
            logging.error(f"Database connection failed: {str(e)}")
            raise

    def create_tables(self):
        """Create all necessary tables"""
        try:
            # Game table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Game (
                    gameId INTEGER PRIMARY KEY,
                    gameDate DATE,
                    season INTEGER,
                    week INTEGER,
                    gameTimeEastern TEXT,
                    homeTeam TEXT,
                    visitorTeam TEXT,
                    homeFinalScore INTEGER,
                    visitorFinalScore INTEGER
                )
            ''')

            # Team table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Team (
                    teamAbbreviation TEXT PRIMARY KEY,
                    teamName TEXT
                )
            ''')

            # College table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS College (
                    collegeId INTEGER PRIMARY KEY AUTOINCREMENT,
                    collegeName TEXT UNIQUE
                )
            ''')

            # Player table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Player (
                    nflId INTEGER PRIMARY KEY,
                    displayName TEXT,
                    height TEXT,
                    weight FLOAT,
                    birthDate DATE,
                    position TEXT,
                    collegeId INTEGER,
                    FOREIGN KEY (collegeId) REFERENCES College(collegeId)
                )
            ''')

            # Plays table (added based on available data)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Play (
                    gameId INTEGER,
                    playId INTEGER,
                    ballCarrierId INTEGER,
                    quarter INTEGER,
                    down INTEGER,
                    yardsToGo INTEGER,
                    possessionTeam TEXT,
                    playResult INTEGER,
                    passProbability FLOAT,
                    expectedPoints FLOAT,
                    PRIMARY KEY (gameId, playId),
                    FOREIGN KEY (gameId) REFERENCES Game(gameId),
                    FOREIGN KEY (ballCarrierId) REFERENCES Player(nflId)
                )
            ''')

            # Tackles table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Tackles (
                    gameId INTEGER,
                    playId INTEGER,
                    nflId INTEGER,
                    tackle INTEGER,
                    assist INTEGER,
                    forcedFumble INTEGER,
                    missedTackle INTEGER,
                    PRIMARY KEY (gameId, playId, nflId),
                    FOREIGN KEY (gameId, playId) REFERENCES Play(gameId, playId),
                    FOREIGN KEY (nflId) REFERENCES Player(nflId)
                )
            ''')
            
                # Add Nominees table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Awards (
                    awardId INTEGER PRIMARY KEY AUTOINCREMENT,
                    awardName TEXT UNIQUE
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Nominees (
                    awardId INTEGER,
                    nflId INTEGER,
                    FOREIGN KEY (awardId) REFERENCES Awards(awardId),
                    FOREIGN KEY (nflId) REFERENCES Player(nflId),
                    PRIMARY KEY (awardId, nflId)
                )
            ''')

            self.conn.commit()
            logging.info("Tables created successfully")
        except Exception as e:
            logging.error(f"Table creation failed: {str(e)}")
            raise

    def process_games(self, file_path):
        """Process games.csv"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Games file not found: {file_path}")

            df = pd.read_csv(file_path)
            logging.info(f"Processing {len(df)} games records")
            
            # Validate required columns
            required_columns = ['gameId', 'gameDate', 'season', 'week', 'gameTimeEastern',
                            'homeTeamAbbr', 'visitorTeamAbbr', 'homeFinalScore', 'visitorFinalScore']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            # Data cleaning and validation
            df['gameDate'] = pd.to_datetime(df['gameDate'], errors='coerce')
            df['gameId'] = pd.to_numeric(df['gameId'], errors='coerce')
            df['season'] = pd.to_numeric(df['season'], errors='coerce')
            df['week'] = pd.to_numeric(df['week'], errors='coerce')
            df['homeFinalScore'] = pd.to_numeric(df['homeFinalScore'], errors='coerce')
            df['visitorFinalScore'] = pd.to_numeric(df['visitorFinalScore'], errors='coerce')

            # Drop rows with critical null values
            critical_columns = ['gameId', 'gameDate', 'homeTeamAbbr', 'visitorTeamAbbr']
            df_clean = df.dropna(subset=critical_columns)
            
            if len(df_clean) < len(df):
                logging.warning(f"Dropped {len(df) - len(df_clean)} rows with missing critical data")

            # Get unique teams
            teams = set(df_clean['homeTeamAbbr'].unique()) | set(df_clean['visitorTeamAbbr'].unique())
            teams = {team for team in teams if pd.notna(team)}  # Remove any NaN values
            
            for team in tqdm(teams, desc="Processing teams"):
                self.cursor.execute(
                    "INSERT OR IGNORE INTO Team (teamAbbreviation) VALUES (?)",
                    (team,)
                )

            # Insert games
            for _, row in tqdm(df_clean.iterrows(), total=len(df_clean), desc="Processing games"):
                try:
                    self.cursor.execute('''
                        INSERT OR REPLACE INTO Game 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        int(row['gameId']), 
                        row['gameDate'].strftime('%Y-%m-%d') if pd.notna(row['gameDate']) else None,
                        int(row['season']) if pd.notna(row['season']) else None,
                        int(row['week']) if pd.notna(row['week']) else None,
                        row['gameTimeEastern'],
                        row['homeTeamAbbr'],
                        row['visitorTeamAbbr'],
                        int(row['homeFinalScore']) if pd.notna(row['homeFinalScore']) else None,
                        int(row['visitorFinalScore']) if pd.notna(row['visitorFinalScore']) else None
                    ))
                except Exception as e:
                    logging.error(f"Error inserting game {row['gameId']}: {str(e)}")
                    continue

            self.conn.commit()
            logging.info("Games data processed successfully")
        except Exception as e:
            logging.error(f"Games processing failed: {str(e)}")
            self.conn.rollback()  # Rollback changes if there's an error
            raise


    def process_players(self, file_path):
        """Process players.csv"""
        try:
            df = pd.read_csv(file_path)
            logging.info(f"Processing {len(df)} player records")

            # Process colleges first
            colleges = df['collegeName'].dropna().unique()
            for college in tqdm(colleges, desc="Processing colleges"):
                self.cursor.execute(
                    "INSERT OR IGNORE INTO College (collegeName) VALUES (?)",
                    (college,)
                )

            # Create college name to ID mapping
            college_mapping = {}
            self.cursor.execute("SELECT collegeId, collegeName FROM College")
            for college_id, college_name in self.cursor.fetchall():
                college_mapping[college_name] = college_id

            # Process players
            for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing players"):
                college_id = college_mapping.get(row['collegeName']) if pd.notna(row['collegeName']) else None
                
                self.cursor.execute('''
                    INSERT OR REPLACE INTO Player 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['nflId'], row['displayName'], row['height'],
                    row['weight'], row['birthDate'], row['position'],
                    college_id
                ))

            self.conn.commit()
            logging.info("Players data processed successfully")
        except Exception as e:
            logging.error(f"Players processing failed: {str(e)}")
            raise

    def process_plays(self, file_path):
        """Process plays.csv"""
        try:
            # Read in chunks due to potentially large file size
            chunk_size = 10000
            for chunk in tqdm(pd.read_csv(file_path, chunksize=chunk_size), desc="Processing plays"):
                # Select relevant columns and clean data
                plays_data = chunk[[
                    'gameId', 'playId', 'ballCarrierId', 'quarter', 'down',
                    'yardsToGo', 'possessionTeam', 'playResult', 'passProbability',
                    'expectedPoints'
                ]].copy()

                for _, row in plays_data.iterrows():
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO Play 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', tuple(row))

                self.conn.commit()
            logging.info("Plays data processed successfully")
        except Exception as e:
            logging.error(f"Plays processing failed: {str(e)}")
            raise

    def process_tackles(self, file_path):
        """Process tackles.csv"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Tackles file not found: {file_path}")

            # Read CSV with explicit data types
            df = pd.read_csv(file_path)
            logging.info(f"Processing {len(df)} tackle records")

            # Validate required columns
            required_columns = ['gameId', 'playId', 'nflId', 'tackle', 'assist', 
                            'forcedFumble', 'pff_missedTackle']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            # Convert and clean data
            df['gameId'] = pd.to_numeric(df['gameId'], errors='coerce')
            df['playId'] = pd.to_numeric(df['playId'], errors='coerce')
            df['nflId'] = pd.to_numeric(df['nflId'], errors='coerce')
            
            # Convert boolean/binary columns
            binary_columns = ['tackle', 'assist', 'forcedFumble', 'pff_missedTackle']
            for col in binary_columns:
                df[col] = df[col].fillna(0).astype(int)

            # Drop rows with missing critical data
            df_clean = df.dropna(subset=['gameId', 'playId', 'nflId'])
            
            if len(df_clean) < len(df):
                logging.warning(f"Dropped {len(df) - len(df_clean)} rows with missing critical data")

            # Recreate Tackles table with explicit column types
            self.cursor.execute('''
                DROP TABLE IF EXISTS Tackles
            ''')
            
            self.cursor.execute('''
                CREATE TABLE Tackles (
                    gameId INTEGER,
                    playId INTEGER,
                    nflId INTEGER,
                    tackle INTEGER,
                    assist INTEGER,
                    forcedFumble INTEGER,
                    missedTackle INTEGER,
                    PRIMARY KEY (gameId, playId, nflId),
                    FOREIGN KEY (gameId, playId) REFERENCES Play(gameId, playId),
                    FOREIGN KEY (nflId) REFERENCES Player(nflId)
                )
            ''')

            # Insert data in batches
            batch_size = 1000
            total_batches = len(df_clean) // batch_size + 1
            
            for i in tqdm(range(total_batches), desc="Processing tackles"):
                batch = df_clean.iloc[i*batch_size:(i+1)*batch_size]
                
                for _, row in batch.iterrows():
                    try:
                        self.cursor.execute('''
                            INSERT OR REPLACE INTO Tackles 
                            (gameId, playId, nflId, tackle, assist, forcedFumble, missedTackle)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            int(row['gameId']),
                            int(row['playId']),
                            int(row['nflId']),
                            int(row['tackle']),
                            int(row['assist']),
                            int(row['forcedFumble']),
                            int(row['pff_missedTackle'])
                        ))
                    except Exception as e:
                        logging.error(f"Error inserting tackle record: gameId={row['gameId']}, "
                                    f"playId={row['playId']}, nflId={row['nflId']}, Error: {str(e)}")
                        continue
                
                self.conn.commit()  # Commit after each batch

            logging.info("Tackles data processed successfully")
            
            # Verify data
            self.cursor.execute("SELECT COUNT(*) FROM Tackles")
            count = self.cursor.fetchone()[0]
            logging.info(f"Total tackles records inserted: {count}")
            
        except Exception as e:
            logging.error(f"Tackles processing failed: {str(e)}")
            self.conn.rollback()
            raise
        
    def verify_data(self):
        """Verify data in all tables"""
        try:
            tables = ['Game', 'Team', 'Player', 'Play', 'Tackles']
            for table in tables:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cursor.fetchone()[0]
                logging.info(f"Table {table}: {count} records")
                
                # Sample data verification
                self.cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                sample = self.cursor.fetchone()
                logging.info(f"Sample record from {table}: {sample}")
                
        except Exception as e:
            logging.error(f"Data verification failed: {str(e)}")
            raise

                
    def process_nominees(self, file_path):
        """Process nominees.csv and link to existing players"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Nominees file not found: {file_path}")

            df = pd.read_csv(file_path)
            logging.info(f"Processing {len(df)} nominee records")

            # Get existing players from the database
            self.cursor.execute("SELECT nflId, displayName FROM Player")
            players_db = {name.lower(): id for id, name in self.cursor.fetchall()}

            # Insert awards
            unique_awards = df['Award'].unique()
            for award in unique_awards:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO Awards (awardName) VALUES (?)",
                    (award,)
                )
            
            # Create award name to ID mapping
            self.cursor.execute("SELECT awardId, awardName FROM Awards")
            award_mapping = {name: id for id, name in self.cursor.fetchall()}

            # Process nominees
            nominations_added = 0
            nominations_skipped = 0

            for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing nominees"):
                award_id = award_mapping.get(row['Award'])
                nominee_name = row['Nominee'].lower()
                
                # Skip non-player awards (like team celebrations or coaches)
                if any(skip_term in nominee_name for skip_term in 
                    ['celebration', 'class of', 'award', 'coach']):
                    nominations_skipped += 1
                    continue

                # Try to find the player ID
                player_id = players_db.get(nominee_name)
                
                if player_id and award_id:
                    try:
                        self.cursor.execute('''
                            INSERT OR IGNORE INTO Nominees (awardId, nflId)
                            VALUES (?, ?)
                        ''', (award_id, player_id))
                        nominations_added += 1
                    except sqlite3.IntegrityError as e:
                        logging.warning(f"Couldn't add nominee {row['Nominee']} for {row['Award']}: {str(e)}")
                        nominations_skipped += 1
                else:
                    logging.warning(f"Couldn't find player ID for nominee: {row['Nominee']}")
                    nominations_skipped += 1

            self.conn.commit()
            logging.info(f"Nominees processing completed. Added: {nominations_added}, Skipped: {nominations_skipped}")

        except Exception as e:
            logging.error(f"Nominees processing failed: {str(e)}")
            self.conn.rollback()
            raise
        
    def process_all(self, games_path, players_path, plays_path, tackles_path, nominees_path):
        try:
            self.connect_db()
            self.create_tables()
            
            self.process_games(games_path)
            self.process_players(players_path)
            self.process_plays(plays_path)
            self.process_tackles(tackles_path)
            self.process_nominees(nominees_path)
            
            self.verify_data()
            
            logging.info("All data processed and verified successfully")
        except Exception as e:
            logging.error(f"Data processing failed: {str(e)}")
            raise
        finally:
            if self.conn:
                self.conn.close()

def main():
    etl = NFLDataETL()
    etl.process_all(
        games_path='big_data/games.csv',
        players_path='big_data/players.csv',
        plays_path='big_data/plays.csv',
        tackles_path='big_data/tackles.csv',
        nominees_path='big_data/nominees.csv'
    )

if __name__ == "__main__":
    main()
