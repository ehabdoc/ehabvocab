import sqlite3
import os

def make_admin(username):
    """Sets the is_admin flag to 1 for the specified user."""
    conn = None
    try:
        DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocab_app.db')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
        conn.commit()
        # Check if the update was successful
        cursor.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result and result[0] == 1:
            print(f"Successfully made '{username}' an administrator.")
        else:
            print(f"Error: Could not verify admin status for '{username}'. Was the user registered first?")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    make_admin('ehabdoc')
