import sqlite3
import os
from werkzeug.security import generate_password_hash

# --- IMPORTANT ---
# This script is designed to be run ON the PythonAnywhere server.
# It assumes the database 'vocab_app.db' is in the same directory.

DB_NAME = 'vocab_app.db'
ADMIN_USERNAME = 'ehabtech'
ADMIN_PASSWORD = 'SALafi86' # This will reset the password as well

def grant_admin_privileges():
    """
    Connects to the database and grants admin rights to a user.
    If the user doesn't exist, it creates them as an admin.
    """
    # The path to the database on PythonAnywhere is relative to the script's location
    db_path = os.path.join(os.path.dirname(__file__), DB_NAME)

    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        print("Please make sure this script is in the same directory as your app.py and vocab_app.db on PythonAnywhere.")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,))
        user = cursor.fetchone()

        hashed_password = generate_password_hash(ADMIN_PASSWORD)

        if user:
            # User exists, update them to be an admin
            cursor.execute("UPDATE users SET password = ?, is_admin = 1 WHERE username = ?", (hashed_password, ADMIN_USERNAME))
            print(f"Successfully updated user '{ADMIN_USERNAME}' to be an administrator.")
        else:
            # User does not exist, create them as an admin
            cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)",
                           (ADMIN_USERNAME, hashed_password))
            print(f"Successfully created new administrator user '{ADMIN_USERNAME}'.")

        conn.commit()
        print("Changes have been committed to the database.")

    except sqlite3.Error as e:
        print(f"A database error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    grant_admin_privileges()
