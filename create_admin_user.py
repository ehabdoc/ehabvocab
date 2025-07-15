import sqlite3
import os
from werkzeug.security import generate_password_hash

# Define the path to the database relative to this script
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocab_app.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    return conn

def create_admin(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                       (username, hashed_password, 1))
        conn.commit()
        print(f"Administrator user '{username}' created successfully.")
    except sqlite3.IntegrityError:
        print(f"Error: Username '{username}' already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    admin_username = "ehabtech"
    admin_password = "SALafi86" # Please consider changing this password after creation for security
    create_admin(admin_username, admin_password)
