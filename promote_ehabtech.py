
import sqlite3
import os

# --- Configuration ---
DB_FILE = 'vocab_app.db'
USERNAME_TO_PROMOTE = 'ehabtech'

def promote_user_to_admin():
    """Finds a user by username and sets their is_admin flag to 1."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILE)
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at '{db_path}'")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # First, check if the user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (USERNAME_TO_PROMOTE,))
        user = cursor.fetchone()

        if user:
            # User exists, proceed with update
            print(f"Found user '{USERNAME_TO_PROMOTE}'. Promoting to admin...")
            cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (USERNAME_TO_PROMOTE,))
            conn.commit()

            # Verify the change
            cursor.execute("SELECT is_admin FROM users WHERE username = ?", (USERNAME_TO_PROMOTE,))
            updated_user = cursor.fetchone()
            if updated_user and updated_user[0] == 1:
                print(f"Successfully promoted '{USERNAME_TO_PROMOTE}' to an administrator.")
            else:
                print(f"Error: Failed to verify admin status for '{USERNAME_TO_PROMOTE}'.")
        else:
            print(f"Error: User '{USERNAME_TO_PROMOTE}' not found in the database.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    promote_user_to_admin()
