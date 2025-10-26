import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocab_app.db')

def query_db():
    """Connects to the DB and fetches sample alternatives."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("--- Checking 10 random words with alternatives ---")
        # Query for words that are supposed to have alternatives
        cursor.execute("SELECT english_word, alternative_translations FROM words WHERE alternative_translations != '' AND alternative_translations IS NOT NULL ORDER BY RANDOM() LIMIT 10;")
        rows = cursor.fetchall()
        
        if not rows:
            print("No words with alternatives were found in the database.")
        else:
            for row in rows:
                print(f"English: {row[0]}, Alternatives: {row[1]}")
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    query_db()
