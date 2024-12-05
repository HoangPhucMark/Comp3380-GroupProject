import sqlite3
import os
import sys
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import re

class NFLDatabaseInterface:
    def __init__(self, db_path: str = 'nfl_database.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.page_size = 20
        self.connect_db()

    def connect_db(self) -> None:
        """Establish database connection with error handling"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            # Enable foreign key support
            self.cursor.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            self.display_error(f"Database connection failed: {str(e)}")
            sys.exit(1)

    def create_table_display(self, headers: List[str], data: List[Tuple],
                             min_width: int = 15) -> str:
        """Create a formatted table string without external dependencies"""
        # Calculate column widths
        col_widths = [max(min_width, len(str(h))) for h in headers]
        for row in data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Create separator line
        separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'

        # Create header
        header = '|' + '|'.join(
            f' {h:<{w}} ' for h, w in zip(headers, col_widths)
        ) + '|'

        # Create rows
        rows = []
        for row in data:
            rows.append('|' + '|'.join(
                f' {str(cell):<{w}} ' for cell, w in zip(row, col_widths)
            ) + '|')

        # Combine all parts
        return '\n'.join([
            separator,
            header,
            separator,
            *rows,
            separator
        ])

    def clear_screen(self) -> None:
        """Clear console screen across platforms"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def create_header(self, title: str, width: int = 80) -> str:
        """Create a formatted header"""
        padding = (width - len(title)) // 2
        return (
            f"+{'-' * width}+\n"
            f"|{' ' * padding}{title}{' ' * (width - padding - len(title))}|\n"
            f"+{'-' * width}+"
        )

    def display_error(self, message: str) -> None:
        """Display formatted error message with logging"""
        self.clear_screen()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_display = (
            self.create_header("ERROR", 60) + "\n\n" +
            f"Time: {timestamp}\n" +
            f"Error: {message}\n\n" +
            "Press Enter to continue..."
        )
        print(error_display)
        # Log error to file
        with open('nfl_interface_error.log', 'a') as f:
            f.write(f"{timestamp}: {message}\n")
        input()

    def validate_input(self, input_str: str, input_type: str) -> bool:
        """
        Comprehensive input validation for different types of data
        """
        validation_patterns = {
            'name': r'^[a-zA-Z\s\'-]{2,50}$',
            'id': r'^\d{1,10}$',
            'team': r'^[A-Z]{2,3}$',
            'position': r'^[A-Z]{1,3}$',
            'date': r'^\d{4}-\d{2}-\d{2}$',
            'number': r'^\d+$',
            'score': r'^\d{1,3}$',
            'year': r'^\d{4}$'
        }

        if input_type not in validation_patterns:
            return False

        pattern = validation_patterns[input_type]
        return bool(re.match(pattern, input_str))

    def sanitize_input(self, input_str: str) -> str:
        """Sanitize input to prevent SQL injection"""
        return re.sub(r'[;\'\"\\]', '', input_str)

    def format_player_stats(self, stats: Dict[str, Any]) -> str:
        """Format player statistics for display"""
        stats_display = [
            self.create_header(f"Player Statistics: {stats.get('displayName', 'Unknown')}"),
            "\nBasic Information:",
            f"Position: {stats.get('position', 'N/A')}",
            f"Height: {stats.get('height', 'N/A')}",
            f"Weight: {stats.get('weight', 'N/A')} lbs",
            f"College: {stats.get('collegeName', 'N/A')}",
            "\nPerformance Statistics:",
            f"Games Played: {stats.get('games_played', 0)}",
            f"Total Tackles: {stats.get('total_tackles', 0)}",
            f"Solo Tackles: {stats.get('solo_tackles', 0)}",
            f"Assists: {stats.get('assists', 0)}",
            f"Forced Fumbles: {stats.get('forced_fumbles', 0)}",
            f"Missed Tackles: {stats.get('missed_tackles', 0)}"
        ]
        return '\n'.join(stats_display)

    def paginate_results(self, results: List[Tuple], headers: List[str],
                         title: str) -> bool:
        """Display results with pagination and navigation"""
        total_records = len(results)
        total_pages = (total_records + self.page_size - 1) // self.page_size
        current_page = 1

        while True:
            self.clear_screen()
            start_idx = (current_page - 1) * self.page_size
            end_idx = min(start_idx + self.page_size, total_records)
            
            print(self.create_header(title))
            print(f"\nShowing records {start_idx + 1}-{end_idx} of {total_records}")
            
            current_data = results[start_idx:end_idx]
            print(self.create_table_display(headers, current_data))
            
            print("\nNavigation:")
            print("[N]ext page | [P]revious page | [J]ump to page |")
            print("[F]ilter results | [S]ort | [B]ack to menu | [Q]uit")
            
            command = input("\nEnter command: ").lower()

            if command == 'n' and current_page < total_pages:
                current_page += 1
            elif command == 'p' and current_page > 1:
                current_page -= 1
            elif command == 'j':
                try:
                    page = int(input(f"Enter page number (1-{total_pages}): "))
                    if 1 <= page <= total_pages:
                        current_page = page
                    else:
                        self.display_error("Invalid page number")
                except ValueError:
                    self.display_error("Invalid input")
            elif command == 'b':
                return True
            elif command == 'q':
                return False
            elif command == 'f':
                self.filter_results(results, headers)
                return True
            elif command == 's':
                self.sort_results(results, headers)
                return True

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Tuple]]:
        """Execute SQL query with error handling"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.display_error(f"Database error: {str(e)}")
            return None

    def player_menu(self) -> None:
        """Player menu implementation"""
        while True:
            self.clear_screen()
            print(self.create_header("Player Menu"))
            print("\n1. Advanced Player Search")
            print("2. View Player Statistics")
            print("3. Top Performers")
            print("4. Player Comparison")
            print("5. Position Analysis")
            print("6. Career Statistics")
            print("7. Back to Main Menu")
            
            choice = input("\nEnter your choice (1-7): ")
            
            menu_options = {
                '1': self.advanced_player_search,
                '2': self.view_player_statistics,
                '3': self.display_top_performers,
                '4': self.compare_players,
                '5': self.position_analysis,
                '6': self.career_statistics,
                '7': lambda: None
            }

            if choice in menu_options:
                if choice == '7':
                    break
                menu_options[choice]()
            else:
                self.display_error("Invalid choice")

    def advanced_player_search(self) -> None:
        """Advanced player search with multiple criteria"""
        self.clear_screen()
        print(self.create_header("Advanced Player Search"))
        
        # Build search criteria
        criteria = {}
        params = []
        query_conditions = []

        # Name search
        name = input("\nPlayer Name (press Enter to skip): ").strip()
        if name:
            if self.validate_input(name, 'name'):
                query_conditions.append("p.displayName LIKE ?")
                params.append(f"%{self.sanitize_input(name)}%")
            else:
                self.display_error("Invalid name format")
                return

        # Position search
        position = input("Position (e.g., QB, WR, press Enter to skip): ").strip().upper()
        if position:
            if self.validate_input(position, 'position'):
                query_conditions.append("p.position = ?")
                params.append(position)
            else:
                self.display_error("Invalid position format")
                return

        # Height range
        min_height = input("Minimum height in inches (press Enter to skip): ").strip()
        if min_height:
            if min_height.isdigit():
                query_conditions.append("p.height >= ?")
                params.append(int(min_height))
            else:
                self.display_error("Invalid height format")
                return

        # Weight range
        min_weight = input("Minimum weight in lbs (press Enter to skip): ").strip()
        if min_weight:
            if min_weight.isdigit():
                query_conditions.append("p.weight >= ?")
                params.append(int(min_weight))
            else:
                self.display_error("Invalid weight format")
                return

        # Build the query
        query = """
            SELECT 
                p.nflId,
                p.displayName,
                p.position,
                p.height,
                p.weight,
                c.collegeName,
                COUNT(DISTINCT t.gameId) as games_played,
                SUM(t.tackle) as total_tackles,
                SUM(t.assist) as total_assists,
                SUM(t.forcedFumble) as forced_fumbles
            FROM Player p
            LEFT JOIN College c ON p.collegeId = c.collegeId
            LEFT JOIN Tackles t ON p.nflId = t.nflId
        """

        if query_conditions:
            query += " WHERE " + " AND ".join(query_conditions)

        query += """
            GROUP BY p.nflId, p.displayName, p.position, p.height, p.weight, c.collegeName
            ORDER BY p.displayName
        """

        try:
            results = self.execute_query(query, tuple(params))
            if not results:
                self.display_error("No players found matching the criteria")
                return

            headers = [
                'NFL ID', 'Name', 'Position', 'Height', 'Weight', 'College',
                'Games', 'Tackles', 'Assists', 'Forced Fumbles'
            ]
            self.paginate_results(results, headers, "Player Search Results")

        except sqlite3.Error as e:
            self.display_error(f"Database error: {str(e)}")

    def view_player_statistics(self) -> None:
        """View detailed statistics for a specific player"""
        self.clear_screen()
        print(self.create_header("Player Statistics"))

        player_id = input("\nEnter player NFL ID (or name to search): ").strip()
        
        if player_id.isdigit():
            self.display_player_details(int(player_id))
        else:
            # Search by name
            query = """
                SELECT nflId, displayName, position 
                FROM Player 
                WHERE displayName LIKE ?
            """
            results = self.execute_query(query, (f"%{self.sanitize_input(player_id)}%",))
            
            if not results:
                self.display_error("No players found with that name")
                return
            
            # If multiple players found, let user choose
            if len(results) > 1:
                print("\nMultiple players found:")
                for i, (pid, name, pos) in enumerate(results, 1):
                    print(f"{i}. {name} ({pos}) - ID: {pid}")
                
                choice = input("\nSelect player number: ")
                if choice.isdigit() and 1 <= int(choice) <= len(results):
                    self.display_player_details(results[int(choice)-1][0])
                else:
                    self.display_error("Invalid selection")
            else:
                self.display_player_details(results[0][0])

    def display_player_details(self, player_id: int) -> None:
        """Display comprehensive player statistics"""
        query = """
            SELECT 
                p.displayName,
                p.position,
                p.height,
                p.weight,
                c.collegeName,
                COUNT(DISTINCT t.gameId) as games_played,
                SUM(t.tackle) as total_tackles,
                SUM(t.assist) as total_assists,
                SUM(t.forcedFumble) as forced_fumbles,
                SUM(t.pff_missedTackle) as missed_tackles,
                (CAST(SUM(t.tackle) + SUM(t.assist) AS FLOAT) / 
                    NULLIF(COUNT(DISTINCT t.gameId), 0)) as tackles_per_game
            FROM Player p
            LEFT JOIN College c ON p.collegeId = c.collegeId
            LEFT JOIN Tackles t ON p.nflId = t.nflId
            WHERE p.nflId = ?
            GROUP BY p.nflId
        """
        
        try:
            result = self.execute_query(query, (player_id,))
            if not result:
                self.display_error("Player not found")
                return

            player_data = result[0]
            
            # Calculate additional statistics
            height_ft = f"{player_data[2] // 12}'{player_data[2] % 12}\""
            bmi = (player_data[3] * 703) / (player_data[2] ** 2)

            # Display formatted statistics
            self.clear_screen()
            print(self.create_header(f"Player Profile: {player_data[0]}"))
            print("\nBasic Information:")
            print(f"Position: {player_data[1]}")
            print(f"Height: {height_ft}")
            print(f"Weight: {player_data[3]} lbs")
            print(f"BMI: {bmi:.1f}")
            print(f"College: {player_data[4] or 'N/A'}")

            print("\nPerformance Statistics:")
            print(f"Games Played: {player_data[5] or 0}")
            print(f"Total Tackles: {player_data[6] or 0}")
            print(f"Total Assists: {player_data[7] or 0}")
            print(f"Forced Fumbles: {player_data[8] or 0}")
            print(f"Missed Tackles: {player_data[9] or 0}")
            print(f"Tackles Per Game: {player_data[10]:.2f}")

            # Get recent games
            recent_games_query = """
                SELECT 
                    g.gameDate,
                    g.homeTeam,
                    g.visitorTeam,
                    t.tackle,
                    t.assist,
                    t.forcedFumble
                FROM Game g
                JOIN Tackles t ON g.gameId = t.gameId
                WHERE t.nflId = ?
                ORDER BY g.gameDate DESC
                LIMIT 5
            """
            
            recent_games = self.execute_query(recent_games_query, (player_id,))
            
            if recent_games:
                print("\nRecent Games:")
                headers = ['Date', 'Home', 'Away', 'Tackles', 'Assists', 'Forced Fumbles']
                print(self.create_table_display(headers, recent_games))

            input("\nPress Enter to continue...")

        except sqlite3.Error as e:
            self.display_error(f"Database error: {str(e)}")

    def display_top_performers(self) -> None:
        """Display top performers based on various metrics"""
        while True:
            self.clear_screen()
            print(self.create_header("Top Performers"))
            print("\nSelect category:")
            print("1. Most Tackles")
            print("2. Most Assists")
            print("3. Most Forced Fumbles")
            print("4. Best Tackle Success Rate")
            print("5. Most Consistent Performers")
            print("6. Back to Player Menu")

            choice = input("\nEnter choice (1-6): ")

            queries = {
                '1': """
                    SELECT 
                        p.displayName,
                        p.position,
                        t.teamAbbr,
                        COUNT(DISTINCT tk.gameId) as games_played,
                        SUM(tk.tackle) as total_tackles,
                        ROUND(CAST(SUM(tk.tackle) AS FLOAT) / 
                            COUNT(DISTINCT tk.gameId), 2) as tackles_per_game
                    FROM Player p
                    JOIN Tackles tk ON p.nflId = tk.nflId
                    LEFT JOIN Team t ON p.currentTeam = t.teamId
                    GROUP BY p.nflId
                    HAVING games_played >= 5
                    ORDER BY total_tackles DESC
                    LIMIT 25
                """,
                '2': """
                    SELECT 
                        p.displayName,
                        p.position,
                        t.teamAbbr,
                        COUNT(DISTINCT tk.gameId) as games_played,
                        SUM(tk.assist) as total_assists,
                        ROUND(CAST(SUM(tk.assist) AS FLOAT) / 
                            COUNT(DISTINCT tk.gameId), 2) as assists_per_game
                    FROM Player p
                    JOIN Tackles tk ON p.nflId = tk.nflId
                    LEFT JOIN Team t ON p.currentTeam = t.teamId
                    GROUP BY p.nflId
                    HAVING games_played >= 5
                    ORDER BY total_assists DESC
                    LIMIT 25
                """,
                '3': """
                    SELECT 
                        p.displayName,
                        p.position,
                        t.teamAbbr,
                        COUNT(DISTINCT tk.gameId) as games_played,
                        SUM(tk.forcedFumble) as forced_fumbles,
                        ROUND(CAST(SUM(tk.forcedFumble) AS FLOAT) / 
                            COUNT(DISTINCT tk.gameId), 2) as fumbles_per_game
                    FROM Player p
                    JOIN Tackles tk ON p.nflId = tk.nflId
                    LEFT JOIN Team t ON p.currentTeam = t.teamId
                    GROUP BY p.nflId
                    HAVING games_played >= 5
                    ORDER BY forced_fumbles DESC
                    LIMIT 25
                """,
                '4': """
                    SELECT 
                        p.displayName,
                        p.position,
                        t.teamAbbr,
                        COUNT(DISTINCT tk.gameId) as games_played,
                        SUM(tk.tackle + tk.assist + tk.pff_missedTackle) as total_attempts,
                        SUM(tk.pff_missedTackle) as missed_tackles,
                        ROUND((1 - CAST(SUM(tk.pff_missedTackle) AS FLOAT) / 
                            NULLIF(SUM(tk.tackle + tk.assist + tk.pff_missedTackle), 0)) * 100, 2) 
                            as success_rate
                    FROM Player p
                    JOIN Tackles tk ON p.nflId = tk.nflId
                    LEFT JOIN Team t ON p.currentTeam = t.teamId
                    GROUP BY p.nflId
                    HAVING games_played >= 5 AND total_attempts >= 20
                    ORDER BY success_rate DESC
                    LIMIT 25
                """,
                '5': """
                    WITH GameStats AS (
                        SELECT 
                            p.nflId,
                            p.displayName,
                            p.position,
                            t.teamAbbr,
                            tk.gameId,
                            (tk.tackle + tk.assist) as total_tackles,
                            AVG(tk.tackle + tk.assist) OVER (
                                PARTITION BY p.nflId
                            ) as avg_tackles,
                            STDDEV(tk.tackle + tk.assist) OVER (
                                PARTITION BY p.nflId
                            ) as stddev_tackles
                        FROM Player p
                        JOIN Tackles tk ON p.nflId = tk.nflId
                        LEFT JOIN Team t ON p.currentTeam = t.teamId
                    )
                    SELECT 
                        displayName,
                        position,
                        teamAbbr,
                        COUNT(DISTINCT gameId) as games_played,
                        ROUND(avg_tackles, 2) as avg_tackles_per_game,
                        ROUND(stddev_tackles, 2) as tackle_variation,
                        ROUND(CASE 
                            WHEN avg_tackles > 0 
                            THEN stddev_tackles / avg_tackles 
                            ELSE NULL 
                        END * 100, 2) as coefficient_of_variation
                    FROM GameStats
                    GROUP BY nflId
                    HAVING games_played >= 5
                    ORDER BY coefficient_of_variation ASC
                    LIMIT 25
                """
            }

            headers = {
                '1': ['Name', 'Position', 'Team', 'Games', 'Total Tackles', 'Tackles/Game'],
                '2': ['Name', 'Position', 'Team', 'Games', 'Total Assists', 'Assists/Game'],
                '3': ['Name', 'Position', 'Team', 'Games', 'Forced Fumbles', 'Fumbles/Game'],
                '4': ['Name', 'Position', 'Team', 'Games', 'Attempts', 'Missed', 'Success Rate %'],
                '5': ['Name', 'Position', 'Team', 'Games', 'Avg Tackles', 'Variation', 'CoV %']
            }

            if choice in queries:
                results = self.execute_query(queries[choice])
                if results:
                    self.paginate_results(results, headers[choice], "Top Performers")
                else:
                    self.display_error("No data available")
            elif choice == '6':
                break
            else:
                self.display_error("Invalid choice")

    def compare_players(self) -> None:
        """Compare multiple players' statistics"""
        self.clear_screen()
        print(self.create_header("Player Comparison"))

        # Get players to compare
        players = []
        while len(players) < 5:
            name = input(f"\nEnter player name to compare (or press Enter to finish): ").strip()
            if not name:
                if len(players) < 2:
                    self.display_error("Please select at least 2 players to compare")
                    continue
                break

            query = """
                SELECT nflId, displayName, position 
                FROM Player 
                WHERE displayName LIKE ?
            """
            results = self.execute_query(query, (f"%{self.sanitize_input(name)}%",))

            if not results:
                self.display_error("Player not found")
                continue

            if len(results) > 1:
                print("\nMultiple players found:")
                for i, (pid, pname, pos) in enumerate(results, 1):
                    print(f"{i}. {pname} ({pos})")
                
                choice = input("Select player number: ")
                if choice.isdigit() and 1 <= int(choice) <= len(results):
                    players.append(results[int(choice)-1][0])
                else:
                    self.display_error("Invalid selection")
            else:
                players.append(results[0][0])

        # Get comparison statistics
        if players:
            comparison_query = """
                SELECT 
                    p.displayName,
                    p.position,
                    COUNT(DISTINCT tk.gameId) as games_played,
                    SUM(tk.tackle) as total_tackles,
                    SUM(tk.assist) as total_assists,
                    SUM(tk.forcedFumble) as forced_fumbles,
                    SUM(tk.pff_missedTackle) as missed_tackles,
                    ROUND(CAST(SUM(tk.tackle + tk.assist) AS FLOAT) / 
                        NULLIF(COUNT(DISTINCT tk.gameId), 0), 2) as tackles_per_game,
                    ROUND((1 - CAST(SUM(tk.pff_missedTackle) AS FLOAT) / 
                        NULLIF(SUM(tk.tackle + tk.assist + tk.pff_missedTackle), 0)) * 100, 2) 
                        as success_rate
                FROM Player p
                LEFT JOIN Tackles tk ON p.nflId = tk.nflId
                WHERE p.nflId IN ({})
                GROUP BY p.nflId
            """.format(','.join('?' * len(players)))

            results = self.execute_query(comparison_query, tuple(players))
            
            if results:
                headers = [
                    'Name', 'Pos', 'Games', 'Tackles', 'Assists', 'Forced Fumbles',
                    'Missed', 'Tackles/Game', 'Success %'
                ]
                self.clear_screen()
                print(self.create_table_display(headers, results))
                
                # Calculate and display relative performance
                print("\nRelative Performance (% of max in category):")
                max_values = [max([row[i] for row in results]) for i in range(2, len(headers))]

                for row in results:
                    print(f"\n{row[0]} ({row[1]}):")
                    for i, (value, max_val) in enumerate(zip(row[2:], max_values)):
                        if isinstance(value, (int, float)) and isinstance(max_val, (int, float)) and max_val != 0:
                            percentage = (value / max_val * 100)
                            print(f"{headers[i+2]}: {'█' * int(percentage/5)} {percentage:.1f}%")
                        else:
                            print(f"{headers[i+2]}: N/A")
                input("\nPress Enter to continue...")
            else:
                self.display_error("No data available for comparison")

    def position_analysis(self) -> None:
        """Analyze performance metrics by position"""
        self.clear_screen()
        print(self.create_header("Position Analysis"))

        query = """
            SELECT 
                p.position,
                COUNT(DISTINCT p.nflId) as player_count,
                AVG(p.height) as avg_height,
                AVG(p.weight) as avg_weight,
                SUM(t.tackle) as total_tackles,
                SUM(t.assist) as total_assists,
                SUM(t.forcedFumble) as total_forced_fumbles,
                SUM(t.pff_missedTackle) as total_missed_tackles
            FROM Player p
            LEFT JOIN Tackles t ON p.nflId = t.nflId
            GROUP BY p.position
            ORDER BY p.position
        """
        results = self.execute_query(query)

        if results:
            headers = [
                'Position', 'Players', 'Avg Height', 'Avg Weight', 'Total Tackles',
                'Assists', 'Forced Fumbles', 'Missed Tackles'
            ]
            self.paginate_results(results, headers, "Position Analysis")
        else:
            self.display_error("No data available for position analysis")

    def career_statistics(self) -> None:
        """View career statistics of a player over multiple seasons"""
        self.clear_screen()
        print(self.create_header("Career Statistics"))

        player_id = input("\nEnter player NFL ID (or name to search): ").strip()
        
        if player_id.isdigit():
            self.display_career_statistics(int(player_id))
        else:
            # Search by name
            query = """
                SELECT nflId, displayName, position 
                FROM Player 
                WHERE displayName LIKE ?
            """
            results = self.execute_query(query, (f"%{self.sanitize_input(player_id)}%",))
            
            if not results:
                self.display_error("No players found with that name")
                return
            
            # If multiple players found, let user choose
            if len(results) > 1:
                print("\nMultiple players found:")
                for i, (pid, name, pos) in enumerate(results, 1):
                    print(f"{i}. {name} ({pos}) - ID: {pid}")
                
                choice = input("\nSelect player number: ")
                if choice.isdigit() and 1 <= int(choice) <= len(results):
                    self.display_career_statistics(results[int(choice)-1][0])
                else:
                    self.display_error("Invalid selection")
            else:
                self.display_career_statistics(results[0][0])

    def display_career_statistics(self, player_id: int) -> None:
        """Display career statistics for a player over multiple seasons"""
        query = """
            SELECT 
                strftime('%Y', g.gameDate) as season_year,
                COUNT(DISTINCT g.gameId) as games_played,
                SUM(t.tackle) as total_tackles,
                SUM(t.assist) as total_assists,
                SUM(t.forcedFumble) as forced_fumbles,
                SUM(t.pff_missedTackle) as missed_tackles
            FROM Tackles t
            JOIN Game g ON t.gameId = g.gameId
            WHERE t.nflId = ?
            GROUP BY season_year
            ORDER BY season_year
        """
        results = self.execute_query(query, (player_id,))
        if results:
            headers = ['Season', 'Games', 'Tackles', 'Assists', 'Forced Fumbles', 'Missed Tackles']
            self.clear_screen()
            print(self.create_header(f"Career Statistics for Player ID {player_id}"))
            print(self.create_table_display(headers, results))
            input("\nPress Enter to continue...")
        else:
            self.display_error("No career data available for this player")

    def team_menu(self) -> None:
        """Team analysis menu implementation"""
        while True:
            self.clear_screen()
            print(self.create_header("Team Analysis Menu"))
            print("\n1. Team Performance Dashboard")
            print("2. Team Roster Analysis")
            print("3. Head-to-Head Comparison")
            print("4. Team Statistics Over Time")
            print("5. Position Group Analysis")
            print("6. Back to Main Menu")

            choice = input("\nEnter choice (1-6): ")

            menu_options = {
                '1': self.team_performance_dashboard,
                '2': self.team_roster_analysis,
                '3': self.team_head_to_head,
                '4': self.team_statistics_timeline,
                '5': self.position_group_analysis
            }

            if choice in menu_options:
                menu_options[choice]()
            elif choice == '6':
                break
            else:
                self.display_error("Invalid choice")

    def team_performance_dashboard(self) -> None:
        """Display comprehensive team performance metrics"""
        query = """
            WITH TeamStats AS (
                SELECT 
                    t.teamAbbr,
                    COUNT(DISTINCT g.gameId) as games_played,
                    SUM(CASE 
                        WHEN g.homeTeam = t.teamAbbr THEN g.homeFinalScore
                        ELSE g.visitorFinalScore
                    END) as points_scored,
                    SUM(CASE 
                        WHEN g.homeTeam = t.teamAbbr THEN g.visitorFinalScore
                        ELSE g.homeFinalScore
                    END) as points_allowed,
                    SUM(tk.tackle) as total_tackles,
                    SUM(tk.assist) as total_assists,
                    SUM(tk.forcedFumble) as forced_fumbles,
                    SUM(tk.pff_missedTackle) as missed_tackles
                FROM Team t
                LEFT JOIN Game g ON t.teamAbbr IN (g.homeTeam, g.visitorTeam)
                LEFT JOIN Tackles tk ON (
                    tk.gameId = g.gameId AND 
                    tk.teamAbbr = t.teamAbbr
                )
                GROUP BY t.teamAbbr
            )
            SELECT 
                teamAbbr as Team,
                games_played as Games,
                ROUND(CAST(points_scored AS FLOAT) / games_played, 1) as Pts_Per_Game,
                ROUND(CAST(points_allowed AS FLOAT) / games_played, 1) as Pts_Allowed_Per_Game,
                ROUND(CAST(total_tackles AS FLOAT) / games_played, 1) as Tackles_Per_Game,
                ROUND(CAST(forced_fumbles AS FLOAT) / games_played, 2) as Fumbles_Per_Game,
                ROUND((1 - CAST(missed_tackles AS FLOAT) / 
                    NULLIF(total_tackles + total_assists + missed_tackles, 0)) * 100, 1) as Tackle_Success_Rate
            FROM TeamStats
            ORDER BY points_scored DESC
        """

        results = self.execute_query(query)
        if results:
            headers = ['Team', 'Games', 'PPG', 'PAPG', 'TPG', 'FPG', 'TSR%']
            self.paginate_results(results, headers, "Team Performance Dashboard")
        else:
            self.display_error("No team data available")

    def team_roster_analysis(self) -> None:
        """Analyze team roster composition and performance"""
        team = input("\nEnter team abbreviation (e.g., NE, DAL): ").strip().upper()
        
        if not self.validate_input(team, 'team'):
            self.display_error("Invalid team abbreviation")
            return

        # Position group distribution
        position_query = """
            SELECT 
                p.position,
                COUNT(*) as player_count,
                AVG(p.weight) as avg_weight,
                AVG(p.height) as avg_height,
                COUNT(DISTINCT tk.gameId) as total_games,
                SUM(tk.tackle + tk.assist) as total_tackles
            FROM Player p
            LEFT JOIN Tackles tk ON p.nflId = tk.nflId
            WHERE p.currentTeam = (
                SELECT teamId FROM Team WHERE teamAbbr = ?
            )
            GROUP BY p.position
            ORDER BY player_count DESC
        """

        player_query = """
            SELECT 
                p.displayName,
                p.position,
                p.height,
                p.weight,
                COUNT(DISTINCT tk.gameId) as games_played,
                SUM(tk.tackle) as tackles,
                SUM(tk.assist) as assists,
                SUM(tk.forcedFumble) as forced_fumbles
            FROM Player p
            LEFT JOIN Tackles tk ON p.nflId = tk.nflId
            WHERE p.currentTeam = (
                SELECT teamId FROM Team WHERE teamAbbr = ?
            )
            GROUP BY p.nflId
            ORDER BY p.position, games_played DESC
        """

        pos_results = self.execute_query(position_query, (team,))
        player_results = self.execute_query(player_query, (team,))

        if pos_results and player_results:
            self.clear_screen()
            print(self.create_header(f"Team Roster Analysis: {team}"))

            # Position distribution
            print("\nPosition Group Distribution:")
            pos_headers = ['Position', 'Count', 'Avg Weight', 'Avg Height', 'Games', 'Tackles']
            print(self.create_table_display(pos_headers, pos_results))

            # Player details
            print("\nPlayer Details:")
            player_headers = ['Name', 'Pos', 'Height', 'Weight', 'Games', 'Tackles', 'Assists', 'FF']
            print(self.create_table_display(player_headers, player_results))

            input("\nPress Enter to continue...")
        else:
            self.display_error(f"No data available for team {team}")

    def team_head_to_head(self) -> None:
        """Compare head-to-head performance between teams"""
        team1 = input("\nEnter first team abbreviation: ").strip().upper()
        team2 = input("Enter second team abbreviation: ").strip().upper()

        if not all(self.validate_input(team, 'team') for team in [team1, team2]):
            self.display_error("Invalid team abbreviation(s)")
            return

        query = """
            SELECT 
                g.gameDate as Date,
                CASE 
                    WHEN g.homeTeam = ? THEN g.homeFinalScore
                    ELSE g.visitorFinalScore
                END as Team1_Score,
                CASE 
                    WHEN g.homeTeam = ? THEN g.visitorFinalScore
                    ELSE g.homeFinalScore
                END as Team2_Score,
                SUM(CASE WHEN tk.teamAbbr = ? THEN tk.tackle ELSE 0 END) as Team1_Tackles,
                SUM(CASE WHEN tk.teamAbbr = ? THEN tk.assist ELSE 0 END) as Team1_Assists,
                SUM(CASE WHEN tk.teamAbbr = ? THEN tk.forcedFumble ELSE 0 END) as Team1_FF,
                SUM(CASE WHEN tk.teamAbbr = ? THEN tk.tackle ELSE 0 END) as Team2_Tackles,
                SUM(CASE WHEN tk.teamAbbr = ? THEN tk.assist ELSE 0 END) as Team2_Assists,
                SUM(CASE WHEN tk.teamAbbr = ? THEN tk.forcedFumble ELSE 0 END) as Team2_FF
            FROM Game g
            LEFT JOIN Tackles tk ON g.gameId = tk.gameId
            WHERE (g.homeTeam = ? AND g.visitorTeam = ?) OR (g.homeTeam = ? AND g.visitorTeam = ?)
            GROUP BY g.gameId
            ORDER BY g.gameDate DESC
        """

        params = (team1, team1, team1, team1, team1, team2, team2, team2,
                  team1, team2, team2, team1)
        
        results = self.execute_query(query, params)
        
        if results:
            self.clear_screen()
            print(self.create_header(f"Head-to-Head: {team1} vs {team2}"))

            # Overall statistics
            team1_wins = sum(1 for r in results if r[1] > r[2])
            team2_wins = sum(1 for r in results if r[2] > r[1])
            
            print(f"\nOverall Record:")
            print(f"{team1}: {team1_wins} wins")
            print(f"{team2}: {team2_wins} wins")
            
            # Game details
            headers = ['Date', f'{team1} Score', f'{team2} Score', 
                      f'{team1} Tkl', f'{team1} Ast', f'{team1} FF',
                      f'{team2} Tkl', f'{team2} Ast', f'{team2} FF']
            print("\nGame History:")
            print(self.create_table_display(headers, results))

            # Performance trends
            if len(results) > 1:
                print("\nPerformance Trends:")
                team1_scores = [r[1] for r in results]
                team2_scores = [r[2] for r in results]
                print(f"{team1} Avg Score: {sum(team1_scores)/len(team1_scores):.1f}")
                print(f"{team2} Avg Score: {sum(team2_scores)/len(team2_scores):.1f}")

            input("\nPress Enter to continue...")
        else:
            self.display_error(f"No head-to-head games found between {team1} and {team2}")

    def team_statistics_timeline(self) -> None:
        """View team statistics over multiple seasons"""
        self.clear_screen()
        print(self.create_header("Team Statistics Over Time"))

        team = input("\nEnter team abbreviation (e.g., NE, DAL): ").strip().upper()

        if not self.validate_input(team, 'team'):
            self.display_error("Invalid team abbreviation")
            return

        query = """
            SELECT 
                strftime('%Y', g.gameDate) as season_year,
                COUNT(DISTINCT g.gameId) as games_played,
                SUM(CASE WHEN g.homeTeam = ? THEN g.homeFinalScore ELSE g.visitorFinalScore END) as points_scored,
                SUM(CASE WHEN g.homeTeam = ? THEN g.visitorFinalScore ELSE g.homeFinalScore END) as points_allowed,
                SUM(tk.tackle) as total_tackles,
                SUM(tk.assist) as total_assists,
                SUM(tk.forcedFumble) as forced_fumbles
            FROM Game g
            LEFT JOIN Tackles tk ON g.gameId = tk.gameId AND tk.teamAbbr = ?
            WHERE g.homeTeam = ? OR g.visitorTeam = ?
            GROUP BY season_year
            ORDER BY season_year
        """
        params = (team, team, team, team, team)
        results = self.execute_query(query, params)

        if results:
            headers = ['Season', 'Games', 'Points Scored', 'Points Allowed', 'Tackles', 'Assists', 'Forced Fumbles']
            self.clear_screen()
            print(self.create_header(f"Team Statistics Over Time: {team}"))
            print(self.create_table_display(headers, results))
            input("\nPress Enter to continue...")
        else:
            self.display_error(f"No data available for team {team}")

    def position_group_analysis(self) -> None:
        """Analyze position groups within teams or across the league"""
        self.clear_screen()
        print(self.create_header("Position Group Analysis"))

        print("\n1. Analyze position groups within a team")
        print("2. Analyze position groups across the league")
        choice = input("\nEnter choice (1-2): ")

        if choice == '1':
            team = input("\nEnter team abbreviation (e.g., NE, DAL): ").strip().upper()
            if not self.validate_input(team, 'team'):
                self.display_error("Invalid team abbreviation")
                return
            
            position_query = """
                SELECT 
                    p.position,
                    COUNT(*) as player_count,
                    AVG(p.weight) as avg_weight,
                    AVG(p.height) as avg_height,
                    COUNT(DISTINCT tk.gameId) as total_games,
                    SUM(tk.tackle + tk.assist) as total_tackles
                FROM Player p
                LEFT JOIN Tackles tk ON p.nflId = tk.nflId
                WHERE p.currentTeam = (
                    SELECT teamId FROM Team WHERE teamAbbr = ?
                )
                GROUP BY p.position
                ORDER BY player_count DESC
            """
            results = self.execute_query(position_query, (team,))
            if results:
                headers = ['Position', 'Count', 'Avg Weight', 'Avg Height', 'Games', 'Tackles']
                self.clear_screen()
                print(self.create_header(f"Position Group Analysis for {team}"))
                print(self.create_table_display(headers, results))
                input("\nPress Enter to continue...")
            else:
                self.display_error(f"No data available for team {team}")

        elif choice == '2':
            league_query = """
                SELECT 
                    p.position,
                    COUNT(*) as player_count,
                    AVG(p.weight) as avg_weight,
                    AVG(p.height) as avg_height,
                    COUNT(DISTINCT tk.gameId) as total_games,
                    SUM(tk.tackle + tk.assist) as total_tackles
                FROM Player p
                LEFT JOIN Tackles tk ON p.nflId = tk.nflId
                GROUP BY p.position
                ORDER BY player_count DESC
            """
            results = self.execute_query(league_query)
            if results:
                headers = ['Position', 'Count', 'Avg Weight', 'Avg Height', 'Games', 'Tackles']
                self.clear_screen()
                print(self.create_header("Position Group Analysis - League Wide"))
                print(self.create_table_display(headers, results))
                input("\nPress Enter to continue...")
            else:
                self.display_error(f"No data available for league analysis")
        else:
            self.display_error("Invalid choice")

    def statistical_analysis(self) -> None:
        """Comprehensive statistical analysis and trends"""
        while True:
            self.clear_screen()
            print(self.create_header("Statistical Analysis"))
            print("\n1. League-wide Trends")
            print("2. Performance Distribution Analysis")
            print("3. Correlation Analysis")
            print("4. Outlier Detection")
            print("5. Back to Main Menu")

            choice = input("\nEnter choice (1-5): ")

            if choice == '1':
                self.analyze_league_trends()
            elif choice == '2':
                self.performance_distribution()
            elif choice == '3':
                self.correlation_analysis()
            elif choice == '4':
                self.detect_outliers()
            elif choice == '5':
                break
            else:
                self.display_error("Invalid choice")

    def analyze_league_trends(self) -> None:
        """Analyze league-wide trends over time"""
        query = """
            WITH WeeklyStats AS (
                SELECT 
                    strftime('%Y-%W', g.gameDate) as week,
                    AVG(g.homeFinalScore + g.visitorFinalScore) as avg_total_score,
                    AVG(tk.tackle + tk.assist) as avg_tackles_per_game,
                    SUM(tk.forcedFumble) as total_forced_fumbles
                FROM Game g
                JOIN Tackles tk ON g.gameId = tk.gameId
                GROUP BY week
                ORDER BY week
            )
            SELECT 
                week,
                ROUND(avg_total_score, 2) as avg_score,
                ROUND(avg_tackles_per_game, 2) as avg_tackles,
                total_forced_fumbles as fumbles
            FROM WeeklyStats
        """
        
        results = self.execute_query(query)
        if results:
            headers = ['Week', 'Avg Score', 'Avg Tackles', 'Fumbles']
            print(self.create_table_display(headers, results))
            
            # Calculate trend indicators
            weeks = len(results)
            if weeks > 1:
                score_trend = (results[-1][1] - results[0][1]) / weeks
                tackle_trend = (results[-1][2] - results[0][2]) / weeks
                
                print("\nTrend Analysis:")
                print(f"Scoring Trend: {score_trend:+.2f} points per week")
                print(f"Tackle Trend: {tackle_trend:+.2f} tackles per week")
        
        input("\nPress Enter to continue...")

    def performance_distribution(self) -> None:
        """Analyze performance distribution across the league"""
        query = """
            WITH PlayerStats AS (
                SELECT 
                    p.displayName,
                    p.position,
                    COUNT(DISTINCT tk.gameId) as games_played,
                    ROUND(CAST(SUM(tk.tackle + tk.assist) AS FLOAT) / 
                        NULLIF(COUNT(DISTINCT tk.gameId), 0), 2) as tackles_per_game
                FROM Player p
                JOIN Tackles tk ON p.nflId = tk.nflId
                GROUP BY p.nflId
                HAVING games_played >= 5
            )
            SELECT 
                position,
                COUNT(*) as player_count,
                ROUND(AVG(tackles_per_game), 2) as avg_tackles,
                ROUND(MIN(tackles_per_game), 2) as min_tackles,
                ROUND(MAX(tackles_per_game), 2) as max_tackles,
                ROUND(
                    (SELECT tackles_per_game
                     FROM (
                         SELECT tackles_per_game, 
                                ROW_NUMBER() OVER (ORDER BY tackles_per_game) as rn,
                                COUNT(*) OVER () as cnt
                         FROM PlayerStats ps2
                         WHERE ps2.position = PlayerStats.position
                     )
                     WHERE rn = (cnt + 1)/2
                    ), 2) as median_tackles
            FROM PlayerStats
            GROUP BY position
            ORDER BY avg_tackles DESC
        """
        
        results = self.execute_query(query)
        if results:
            headers = ['Position', 'Players', 'Avg', 'Min', 'Max', 'Median']
            print(self.create_table_display(headers, results))
        
        input("\nPress Enter to continue...")

    def correlation_analysis(self) -> None:
        """Perform correlation analysis between performance metrics"""
        self.clear_screen()
        print(self.create_header("Correlation Analysis"))

        # For simplicity, calculate correlation between tackles and weight

        # Fetch data
        query = """
            SELECT 
                p.weight,
                SUM(tk.tackle + tk.assist) as total_tackles
            FROM Player p
            JOIN Tackles tk ON p.nflId = tk.nflId
            GROUP BY p.nflId
            HAVING COUNT(DISTINCT tk.gameId) >= 5
        """
        results = self.execute_query(query)
        if results:
            weights = [row[0] for row in results if row[0] and row[1]]
            tackles = [row[1] for row in results if row[0] and row[1]]

            if weights and tackles:
                # Calculate correlation coefficient
                import math
                n = len(weights)
                sum_w = sum(weights)
                sum_t = sum(tackles)
                sum_wt = sum(w*t for w, t in zip(weights, tackles))
                sum_w2 = sum(w**2 for w in weights)
                sum_t2 = sum(t**2 for t in tackles)

                numerator = n * sum_wt - sum_w * sum_t
                denominator = math.sqrt((n * sum_w2 - sum_w**2) * (n * sum_t2 - sum_t**2))

                if denominator != 0:
                    correlation = numerator / denominator
                    print(f"\nCorrelation between player weight and total tackles: {correlation:.2f}")
                    input("\nPress Enter to continue...")
                else:
                    self.display_error("Cannot compute correlation (zero denominator)")
            else:
                self.display_error("Insufficient data for correlation analysis")
        else:
            self.display_error("No data available for correlation analysis")

    def detect_outliers(self) -> None:
        """Detect outliers in performance metrics"""
        self.clear_screen()
        print(self.create_header("Outlier Detection"))

        # For simplicity, detect players with tackles per game significantly above or below average
        query = """
            WITH PlayerStats AS (
                SELECT 
                    p.nflId,
                    p.displayName,
                    p.position,
                    COUNT(DISTINCT tk.gameId) as games_played,
                    SUM(tk.tackle + tk.assist) as total_tackles,
                    ROUND(CAST(SUM(tk.tackle + tk.assist) AS FLOAT) / COUNT(DISTINCT tk.gameId), 2) as tackles_per_game
                FROM Player p
                JOIN Tackles tk ON p.nflId = tk.nflId
                GROUP BY p.nflId
                HAVING games_played >= 5
            ),
            Stats AS (
                SELECT 
                    AVG(tackles_per_game) as avg_tpg,
                    (AVG(tackles_per_game * tackles_per_game) - AVG(tackles_per_game) * AVG(tackles_per_game)) AS variance_tpg,
                    (CASE
                        WHEN (AVG(tackles_per_game * tackles_per_game) - AVG(tackles_per_game) * AVG(tackles_per_game)) > 0
                        THEN SQRT(AVG(tackles_per_game * tackles_per_game) - AVG(tackles_per_game) * AVG(tackles_per_game))
                        ELSE 0
                     END) AS stddev_tpg
                FROM PlayerStats
            )
            SELECT 
                ps.displayName,
                ps.position,
                ps.games_played,
                ps.tackles_per_game
            FROM PlayerStats ps, Stats s
            WHERE 
                ps.tackles_per_game > s.avg_tpg + 2 * s.stddev_tpg OR
                ps.tackles_per_game < s.avg_tpg - 2 * s.stddev_tpg
            ORDER BY ps.tackles_per_game DESC
        """
        results = self.execute_query(query)
        if results:
            headers = ['Name', 'Pos', 'Games', 'Tackles/Game']
            self.clear_screen()
            print(self.create_header("Outlier Players in Tackles per Game"))
            print(self.create_table_display(headers, results))
            input("\nPress Enter to continue...")
        else:
            self.display_error("No significant outliers detected")

    def filter_results(self, results: List[Tuple], headers: List[str]) -> bool:
        """Filter results based on user input"""
        self.clear_screen()
        print(self.create_header("Filter Results"))

        print("\nAvailable fields to filter by:")
        for i, header in enumerate(headers, 1):
            print(f"{i}. {header}")

        try:
            field_choice = int(input("\nEnter the number of the field to filter by: "))
            if 1 <= field_choice <= len(headers):
                field_index = field_choice - 1
            else:
                self.display_error("Invalid field selection")
                return True

            filter_value = input(f"Enter value to filter {headers[field_index]} by: ")

            # Perform filtering
            filtered_results = [row for row in results if str(row[field_index]).lower() == filter_value.lower()]
            if filtered_results:
                self.paginate_results(filtered_results, headers, "Filtered Results")
            else:
                self.display_error("No results match the filter criteria")
        except ValueError:
            self.display_error("Invalid input")
        return True  # Return to previous menu

    def sort_results(self, results: List[Tuple], headers: List[str]) -> bool:
        """Sort results based on user input"""
        self.clear_screen()
        print(self.create_header("Sort Results"))

        print("\nAvailable fields to sort by:")
        for i, header in enumerate(headers, 1):
            print(f"{i}. {header}")

        try:
            field_choice = int(input("\nEnter the number of the field to sort by: "))
            if 1 <= field_choice <= len(headers):
                field_index = field_choice - 1
            else:
                self.display_error("Invalid field selection")
                return True

            order = input("Enter sort order (asc/desc): ").strip().lower()
            if order not in ('asc', 'desc'):
                self.display_error("Invalid sort order")
                return True

            reverse = (order == 'desc')
            sorted_results = sorted(results, key=lambda x: x[field_index], reverse=reverse)
            self.paginate_results(sorted_results, headers, "Sorted Results")
        except ValueError:
            self.display_error("Invalid input")
        return True  # Return to previous menu

    # Utility Methods
    def export_data(self, data: List[Tuple], filename: str, headers: List[str]) -> bool:
        """Export data to CSV file"""
        try:
            with open(filename, 'w', newline='') as f:
                f.write(','.join(headers) + '\n')
                for row in data:
                    f.write(','.join(str(item) for item in row) + '\n')
            return True
        except Exception as e:
            self.display_error(f"Export failed: {str(e)}")
            return False

    def export_data_menu(self) -> None:
        """Menu for exporting data"""
        self.clear_screen()
        print(self.create_header("Export Data"))

        print("\nSelect data to export:")
        print("1. Players")
        print("2. Teams")
        print("3. Games")
        print("4. Tackles")
        print("5. Back to Data Management Menu")

        choice = input("\nEnter choice (1-5): ")

        tables = {
            '1': ('Player', "SELECT * FROM Player"),
            '2': ('Team', "SELECT * FROM Team"),
            '3': ('Game', "SELECT * FROM Game"),
            '4': ('Tackles', "SELECT * FROM Tackles"),
        }

        if choice in tables:
            filename = input("\nEnter filename to export data: ").strip()
            if not filename.endswith('.csv'):
                filename += '.csv'
            table_name, query = tables[choice]
            results = self.execute_query(query)
            headers = [description[0] for description in self.cursor.description]
            if self.export_data(results, filename, headers):
                print(f"\nData exported successfully to {filename}")
            input("\nPress Enter to continue...")

        elif choice == '5':
            return
        else:
            self.display_error("Invalid choice")

    def backup_database(self) -> bool:
        """Create a backup of the database"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_nfl_database_{timestamp}.db"
            
            with sqlite3.connect(self.db_path) as src, \
                 sqlite3.connect(backup_path) as dst:
                src.backup(dst)
            return True
        except sqlite3.Error as e:
            self.display_error(f"Backup failed: {str(e)}")
            return False

    def data_management_menu(self) -> None:
        """Data management menu"""
        while True:
            self.clear_screen()
            print(self.create_header("Data Management Menu"))
            print("\n1. Export Data")
            print("2. Backup Database")
            print("3. Clean Up Data")
            print("4. Back to Main Menu")

            choice = input("\nEnter your choice (1-4): ")

            if choice == '1':
                self.export_data_menu()
            elif choice == '2':
                if self.backup_database():
                    print("\nDatabase backup created successfully.")
                input("\nPress Enter to continue...")
            elif choice == '3':
                self.clean_up_data()
            elif choice == '4':
                break
            else:
                self.display_error("Invalid choice")

    def clean_up_data(self) -> None:
        """Clean up data by removing temporary or old data (dummy implementation)"""
        self.clear_screen()
        print(self.create_header("Clean Up Data"))

        # For example, remove old log entries
        try:
            if os.path.exists('nfl_interface_error.log'):
                os.remove('nfl_interface_error.log')
                print("\nOld error logs cleaned up.")
            else:
                print("\nNo error logs to clean.")
        except Exception as e:
            self.display_error(f"Cleanup failed: {str(e)}")
        input("\nPress Enter to continue...")

    def validate_date_range(self, start_date: str, end_date: str) -> bool:
        """Validate date range format and logic"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            return start <= end
        except ValueError:
            return False

    def cleanup(self) -> None:
        """Cleanup database connections and temporary files"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()

def main():
    """Main application entry point"""
    try:
        with NFLDatabaseInterface() as nfl_db:
            while True:
                nfl_db.clear_screen()
                print(nfl_db.create_header("NFL Database Analysis System"))
                print("\n1. Player Analysis")
                print("2. Team Analysis")
                print("3. Statistical Analysis")
                print("4. Data Management")
                print("5. Exit")

                choice = input("\nEnter your choice (1-5): ")

                if choice == '1':
                    nfl_db.player_menu()
                elif choice == '2':
                    nfl_db.team_menu()
                elif choice == '3':
                    nfl_db.statistical_analysis()
                elif choice == '4':
                    nfl_db.data_management_menu()
                elif choice == '5':
                    print("\nThank you for using the NFL Database Analysis System!")
                    break
                else:
                    nfl_db.display_error("Invalid choice")

    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        print("Please contact system administrator.")
    finally:
        print("\nExiting system...")

if __name__ == "__main__":
    main()
