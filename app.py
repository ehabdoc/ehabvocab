import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import csv
import os
from werkzeug.utils import secure_filename
from validators import is_valid_username, is_valid_password, is_valid_word, is_valid_book_name, is_valid_review_input, clean_string

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database Functions ---

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocab_app.db')

def get_db_connection():
    """Establishes a connection to the SQLite database using an absolute path."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')  # Enforce foreign key constraints
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Clears existing data and creates new tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop tables in the correct order to avoid foreign key constraint issues
    cursor.execute("DROP TABLE IF EXISTS user_word_progress")
    cursor.execute("DROP TABLE IF EXISTS words")
    cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()

    # Re-create tables
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english_word TEXT NOT NULL UNIQUE,
            arabic_translation TEXT NOT NULL,
            book_name TEXT DEFAULT 'Uncategorized'
        )
    ''')
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
    conn.commit()
    conn.close()

# Initialize the database when the app starts.
with app.app_context():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

# --- Routes ---

@app.route('/register', methods=('GET', 'POST'))
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = clean_string(request.form['username'])
        password = clean_string(request.form['password'])

        is_valid_user, user_error_message = is_valid_username(username)
        if not is_valid_user:
            flash(user_error_message, 'error')
            return render_template('register.html')

        is_valid_pass, pass_error_message = is_valid_password(password)
        if not is_valid_pass:
            flash(pass_error_message, 'error')
            return render_template('register.html')

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                           (username, generate_password_hash(password)))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash(f'Username "{username}" is already taken.', 'error')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = clean_string(request.form['username'])
        password = clean_string(request.form['password'])

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logs the user out."""
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    """
    Main page.
    - For admins, displays a paginated list of all words.
    - For regular users, displays buttons for each book to start a review session.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT book_name FROM words ORDER BY book_name ASC')
    book_names = [row['book_name'] for row in cursor.fetchall()]

    if session.get('is_admin'):
        page = request.args.get('page', 1, type=int)
        per_page = 50
        book_filter = request.args.get('book_name')

        query = 'SELECT * FROM words'
        count_query = 'SELECT COUNT(*) FROM words'
        params = []

        if book_filter:
            query += ' WHERE book_name = ?'
            count_query += ' WHERE book_name = ?'
            params.append(book_filter)

        total_words = cursor.execute(count_query, tuple(params)).fetchone()[0]
        total_pages = (total_words + per_page - 1) // per_page

        query += ' ORDER BY english_word ASC LIMIT ? OFFSET ?'
        params.extend([per_page, (page - 1) * per_page])

        cursor.execute(query, tuple(params))
        words = cursor.fetchall()
        conn.close()
        return render_template('index.html', words=words, book_names=book_names, selected_book=book_filter,
                               current_page=page, total_pages=total_pages)
    else:
        conn.close()
        return render_template('index.html', book_names=book_names)

@app.route('/import_csv', methods=['GET', 'POST'])
def import_words_from_csv():
    """Page for admins to import words from a CSV file into the global list."""
    if not session.get('is_admin'):
        flash('You must be an admin to import words.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        if not file.filename.endswith('.csv'):
            flash('Invalid file type. Please upload a .csv file.', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = get_db_connection()
        cursor = conn.cursor()
        imported_count, updated_count, skipped_count = 0, 0, 0
        words_per_book = 600

        try:
            with open(filepath, mode='r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                for i, row in enumerate(csv_reader):
                    book_name = f'Book {(i // words_per_book) + 1}'
                    if len(row) < 2:
                        skipped_count += 1
                        app.logger.warning(f'Skipping row {i+1}: not enough columns.')
                        continue

                    english_word, arabic_translation = row[0].strip(), row[1].strip()
                    
                    is_valid_eng, eng_error = is_valid_word(english_word)
                    if not is_valid_eng:
                        skipped_count += 1
                        app.logger.warning(f'Skipping row {i+1}: English word "{english_word}" is invalid: {eng_error}')
                        continue

                    is_valid_ara, ara_error = is_valid_word(arabic_translation)
                    if not is_valid_ara:
                        skipped_count += 1
                        app.logger.warning(f'Skipping row {i+1}: Arabic translation "{arabic_translation}" is invalid: {ara_error}')
                        continue

                    try:
                        cursor.execute("INSERT INTO words (english_word, arabic_translation, book_name) VALUES (?, ?, ?)",
                                       (english_word, arabic_translation, book_name))
                        imported_count += 1
                    except sqlite3.IntegrityError:
                        cursor.execute("UPDATE words SET arabic_translation = ?, book_name = ? WHERE english_word = ?",
                                       (arabic_translation, book_name, english_word))
                        updated_count += 1
            conn.commit()
            flash(f'Import complete: {imported_count} imported, {updated_count} updated, {skipped_count} skipped.', 'success')
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
        finally:
            conn.close()
        return redirect(url_for('index'))
    return render_template('import_csv.html')

@app.route('/review')
def review():
    """Shows a word for the user to review based on their personal progress."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    book_filter = request.args.get('book_name')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT book_name FROM words ORDER BY book_name ASC')
    book_names = [row['book_name'] for row in cursor.fetchall()]

    query = """
        SELECT w.id, w.english_word, w.arabic_translation, w.book_name
        FROM words w
        LEFT JOIN user_word_progress p ON w.id = p.word_id AND p.user_id = ?
        WHERE (p.next_review <= date('now') OR p.word_id IS NULL)
    """
    params = [user_id]

    if book_filter:
        query += ' AND w.book_name = ?'
        params.append(book_filter)

    query += ' ORDER BY p.next_review ASC, RANDOM() LIMIT 1'
    
    word_data = cursor.execute(query, tuple(params)).fetchone()
    conn.close()

    if not word_data:
        flash('No more words to review in this book for now!', 'success')
        return redirect(url_for('index'))

    return render_template('review.html', word=dict(word_data), book_names=book_names, selected_book=book_filter)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    """Processes a review and updates the user's personal progress."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    user_id = session['user_id']
    data = request.get_json()
    word_id = data.get('word_id')
    user_input = data.get('user_input')

    conn = get_db_connection()
    cursor = conn.cursor()

    word_info = cursor.execute('SELECT english_word FROM words WHERE id = ?', (word_id,)).fetchone()
    if not word_info:
        conn.close()
        return jsonify({'success': False, 'message': 'Word not found'}), 404

    progress = cursor.execute('SELECT * FROM user_word_progress WHERE user_id = ? AND word_id = ?', (user_id, word_id)).fetchone()

    # Default values for a word the user has never reviewed
    ease_factor = 2.5
    repetitions = 0
    previous_interval = 1
    if progress:
        ease_factor = progress['ease_factor']
        repetitions = progress['repetitions']
        try:
            last_rev = datetime.strptime(progress['last_reviewed'].split(' ')[0], '%Y-%m-%d').date()
            next_rev = datetime.strptime(progress['next_review'].split(' ')[0], '%Y-%m-%d').date()
            previous_interval = (next_rev - last_rev).days
        except (ValueError, TypeError):
            previous_interval = 1

    is_correct = user_input.strip().lower() == word_info['english_word'].strip().lower()
    quality = 5 if is_correct else 0

    new_ease_factor = max(1.3, ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    
    if is_correct:
        new_repetitions = repetitions + 1
        if new_repetitions <= 1: new_interval = 1
        elif new_repetitions == 2: new_interval = 6
        else: new_interval = int(round(previous_interval * new_ease_factor))
        session['correct_answers'] = session.get('correct_answers', 0) + 1
    else:
        new_repetitions = 0
        new_interval = 1
        session['incorrect_answers'] = session.get('incorrect_answers', 0) + 1

    today = datetime.now().date()
    new_next_review = today + timedelta(days=new_interval)

    if progress:
        cursor.execute('''
            UPDATE user_word_progress
            SET last_reviewed = ?, next_review = ?, repetitions = ?, ease_factor = ?
            WHERE user_id = ? AND word_id = ?
        ''', (today.isoformat(), new_next_review.isoformat(), new_repetitions, new_ease_factor, user_id, word_id))
    else:
        cursor.execute('''
            INSERT INTO user_word_progress (user_id, word_id, last_reviewed, next_review, repetitions, ease_factor)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, word_id, today.isoformat(), new_next_review.isoformat(), new_repetitions, new_ease_factor))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'is_correct': is_correct, 'correct_answer': word_info['english_word']})

@app.route('/session_summary')
def session_summary():
    """Displays a summary of the current review session."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    correct_count = session.get('correct_answers', 0)
    incorrect_count = session.get('incorrect_answers', 0)
    total_words_reviewed = correct_count + incorrect_count

    return render_template('session_summary.html',
                           correct_count=correct_count,
                           incorrect_count=incorrect_count,
                           total_words_reviewed=total_words_reviewed)

@app.route('/statistics')
def statistics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total words reviewed by the user (words in user_word_progress)
    cursor.execute('''
        SELECT COUNT(*) FROM user_word_progress WHERE user_id = ?
    ''', (user_id,))
    total_reviewed_words = cursor.fetchone()[0]

    # Words due for review today
    cursor.execute('''
        SELECT COUNT(*) FROM user_word_progress
        WHERE user_id = ? AND next_review <= date('now')
    ''', (user_id,))
    words_due_today = cursor.fetchone()[0]

    # Words mastered (e.g., repetitions >= 5, this is an arbitrary threshold, can be adjusted)
    cursor.execute('''
        SELECT COUNT(*) FROM user_word_progress
        WHERE user_id = ? AND repetitions >= 5
    ''', (user_id,))
    words_mastered = cursor.fetchone()[0]

    # Average ease factor
    cursor.execute('''
        SELECT AVG(ease_factor) FROM user_word_progress WHERE user_id = ?
    ''', (user_id,))
    avg_ease_factor = cursor.fetchone()[0]
    if avg_ease_factor is None:
        avg_ease_factor = 0.0

    conn.close()

    return render_template('statistics.html',
                           total_reviewed_words=total_reviewed_words,
                           words_due_today=words_due_today,
                           words_mastered=words_mastered,
                           avg_ease_factor=f'{avg_ease_factor:.2f}')

@app.route('/reset_session')
def reset_session():
    """Resets the current review session statistics."""
    session['correct_answers'] = 0
    session['incorrect_answers'] = 0
    flash('Review session statistics have been reset.', 'info')
    return redirect(url_for('review'))

# Admin routes for editing and deleting global words
@app.route('/edit_word/<int:word_id>', methods=['GET', 'POST'])
def edit_word(word_id):
    if not session.get('is_admin'):
        flash('You must be an admin to edit words.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        # ... (validation logic) ...
        english_word = request.form['english_word'].strip()
        arabic_translation = request.form['arabic_translation'].strip()
        book_name = request.form.get('book_name', 'Uncategorized').strip()
        try:
            conn.execute('UPDATE words SET english_word = ?, arabic_translation = ?, book_name = ? WHERE id = ?',
                         (english_word, arabic_translation, book_name, word_id))
            conn.commit()
            flash('Word updated successfully!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash(f'The English word "{english_word}" already exists.', 'error')
        finally:
            conn.close()
    
    word = conn.execute('SELECT * FROM words WHERE id = ?', (word_id,)).fetchone()
    conn.close()
    if word is None:
        flash('Word not found.', 'error')
        return redirect(url_for('index'))
    return render_template('edit_word.html', word=word)

@app.route('/delete_word/<int:word_id>', methods=['POST'])
def delete_word(word_id):
    if not session.get('is_admin'):
        flash('You must be an admin to delete words.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM words WHERE id = ?', (word_id,))
    conn.commit()
    conn.close()
    flash('Word deleted successfully!', 'success')
    return redirect(url_for('index'))

# Admin panel and user management routes remain largely the same
@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch users
    users = cursor.execute('SELECT id, username, is_admin FROM users ORDER BY username ASC').fetchall()

    # Pagination for words
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Words per page

    # Get total words for pagination
    total_words = cursor.execute('SELECT COUNT(*) FROM words').fetchone()[0]
    total_pages = (total_words + per_page - 1) // per_page

    # Fetch words for the current page
    offset = (page - 1) * per_page
    words = cursor.execute('SELECT * FROM words ORDER BY english_word ASC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    
    conn.close()
    
    return render_template('admin_panel.html', 
                           users=users, 
                           words=words,
                           current_page=page,
                           total_pages=total_pages)

@app.route('/make-admin/<int:user_id>')
def make_admin(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('User promoted to admin.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if not session.get('is_admin') or user_id == session['user_id']:
        flash("You cannot delete your own account.", 'error')
        return redirect(url_for('admin_panel'))
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,)) # ON DELETE CASCADE handles progress
    conn.commit()
    conn.close()
    flash('User and their progress have been deleted.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_all_words', methods=['POST'])
def delete_all_words():
    """Deletes all words from the words table."""
    if not session.get('is_admin'):
        flash('You must be an admin to perform this action.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM words')
        # Also clear the progress for all users since the words are gone
        conn.execute('DELETE FROM user_word_progress')
        conn.commit()
        flash('All words have been successfully deleted.', 'success')
    except Exception as e:
        flash(f'An error occurred: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_selected_words', methods=['POST'])
def delete_selected_words():
    """Deletes selected words from the database."""
    if not session.get('is_admin'):
        flash('You must be an admin to perform this action.', 'error')
        return redirect(url_for('index'))

    word_ids_to_delete = request.form.getlist('word_ids')
    if not word_ids_to_delete:
        flash('No words selected for deletion.', 'warning')
        return redirect(url_for('admin_panel'))

    conn = get_db_connection()
    try:
        # Using placeholders to prevent SQL injection
        placeholders = ','.join('?' for _ in word_ids_to_delete)
        query = f'DELETE FROM words WHERE id IN ({placeholders})'
        conn.execute(query, word_ids_to_delete)
        conn.commit()
        flash(f'{len(word_ids_to_delete)} words have been successfully deleted.', 'success')
    except Exception as e:
        flash(f'An error occurred: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_panel'))


import click
from flask.cli import with_appcontext

# ... (rest of the app code) ...

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)

# --- Main Execution ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)