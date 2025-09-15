import sqlite3
import os
from werkzeug.security import generate_password_hash
import getpass

# --- Configuration ---
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocab_app.db')
ADMIN_USERNAME = 'ehabtech'

def create_admin():
    """Creates a new admin user in the database."""
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return

    admin_password = getpass.getpass(f"Enter password for {ADMIN_USERNAME}: ")
    admin_password_confirm = getpass.getpass("Confirm password: ")

    if admin_password != admin_password_confirm:
        print("Passwords do not match.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if the user already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,))
        user = cursor.fetchone()

        if user:
            # If user exists, update their password and make them an admin
            hashed_password = generate_password_hash(admin_password)
            cursor.execute("UPDATE users SET password = ?, is_admin = 1 WHERE username = ?", (hashed_password, ADMIN_USERNAME))
            print(f"Admin user '{ADMIN_USERNAME}' already existed. Password has been updated and admin privileges ensured.")
        else:
            # If user does not exist, create them
            hashed_password = generate_password_hash(admin_password)
            cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)",
                           (ADMIN_USERNAME, hashed_password))
            print(f"Admin user '{ADMIN_USERNAME}' created successfully.")

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    create_admin()
