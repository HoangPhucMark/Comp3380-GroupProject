import sqlite3

def summarize_database(db_path):
    # Connect to the SQLite database
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    
    # Query to get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    summary = []
    
    for table in tables:
        table_name = table[0]
        summary.append(f"Table: {table_name}")
        
        # Query to get column names and types for each table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for column in columns:
            column_name = column[1]
            column_type = column[2]
            summary.append(f"  Column: {column_name} ({column_type})")
    
    # Close the connection
    connection.close()
    
    return "\n".join(summary)

# Path to your database
db_path = 'nfl_database.db'
summary = summarize_database(db_path)
print(summary)
