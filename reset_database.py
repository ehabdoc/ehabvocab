import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocab_app.db')

def reset_database():
    """
    Deletes the existing database file and creates a new one with the correct schema.
    This is a complete and total reset.
    """
    # 1. Delete the old database file if it exists
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed existing database file: {DB_FILE}")

    # 2. Create a new database and tables
    conn = None
    try:
        print("Creating new database and tables...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            )
        ''')
        print("- Created 'users' table.")

        # Create words table
        cursor.execute('''
            CREATE TABLE words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english_word TEXT NOT NULL UNIQUE,
                arabic_translation TEXT NOT NULL,
                book_name TEXT DEFAULT 'Uncategorized'
            )
        ''')
        print("- Created 'words' table.")

        # Create user_word_progress table
        cursor.execute('''
            CREATE TABLE user_word_progress (
                user_id INTEGER NOT NULL,
                word_id INTEGER NOT NULL,
                last_reviewed TEXT DEFAULT (date('now')),
                next_review TEXT DEFAULT (date('now')),
                mastery_level INTEGER DEFAULT 0,
                ease_factor REAL DEFAULT 2.5,
                repetitions INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, word_id),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (word_id) REFERENCES words (id) ON DELETE CASCADE
            )
        ''')
        print("- Created 'user_word_progress' table.")

        conn.commit()
        print("Database has been successfully reset.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    reset_database()
