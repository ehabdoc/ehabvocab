import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import csv
import os
import shutil
from werkzeug.utils import secure_filename
from validators import is_valid_username, is_valid_password, is_valid_word, is_valid_book_name, is_valid_review_input, clean_string

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database Functions ---

DATABASE_URL = os.environ.get('DATABASE_URL')

class DatabaseConnection:
    """Wrapper around psycopg2 connection that mimics sqlite3 connection API."""
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self._rowcount = 0

    def execute(self, query, params=None):
        if params is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, params)
        return self

    def fetchone(self):
        row = self.cursor.fetchone()
        return row  # RealDictRow supports both row['col'] and row[0] access

    def fetchall(self):
        return self.cursor.fetchall()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.cursor.close()
        self.conn.close()

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    conn.autocommit = False
    return DatabaseConnection(conn)

def init_db():
    """Clears existing data and creates new tables."""
    conn = get_db_connection()
    cursor = conn.cursor  # Use the underlying cursor

    # Drop tables in the correct order to avoid foreign key constraint issues
    cursor.execute("DROP TABLE IF EXISTS visitor_stats")
    cursor.execute("DROP TABLE IF EXISTS user_word_progress")
    cursor.execute("DROP TABLE IF EXISTS words")
    cursor.execute("DROP TABLE IF EXISTS users")
    conn.commit()

    # Re-create tables
    create_users_table(cursor)
    create_words_table(cursor)
    create_user_word_progress_table(cursor)
    create_visitor_stats_table(cursor)
    
    conn.commit()
    conn.close()

def create_users_table(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    ''')

def create_words_table(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id SERIAL PRIMARY KEY,
            english_word TEXT NOT NULL,
            vocalized_arabic TEXT,
            alternative_translations TEXT,
            book_name TEXT DEFAULT 'Uncategorized'
        )
    ''')
    try:
        cursor.execute('ALTER TABLE words ADD COLUMN IF NOT EXISTS example_en TEXT')
    except Exception:
        pass

def create_user_word_progress_table(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_word_progress (
            user_id INTEGER NOT NULL,
            word_id INTEGER NOT NULL,
            last_reviewed TEXT DEFAULT (CURRENT_DATE),
            next_review TEXT DEFAULT (CURRENT_DATE),
            mastery_level INTEGER DEFAULT 0,
            ease_factor REAL DEFAULT 2.5,
            repetitions INTEGER DEFAULT 0,
            interval_days INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, word_id),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (word_id) REFERENCES words (id) ON DELETE CASCADE
        )
    ''')

def create_visitor_stats_table(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitor_stats (
            id SERIAL PRIMARY KEY,
            ip_address TEXT NOT NULL,
            user_agent TEXT,
            visit_date DATE NOT NULL,
            UNIQUE(ip_address, visit_date)
        )
    ''')

# Initialize the database when the app starts.
with app.app_context():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if DATABASE_URL:
        conn = get_db_connection()
        cursor = conn.cursor
        create_users_table(cursor)
        create_words_table(cursor)
        create_user_word_progress_table(cursor)
        create_visitor_stats_table(cursor)
        conn.commit()
        conn.close()

@app.before_request
def track_visitor():
    # List of static file extensions to exclude from tracking
    static_extensions = ['.css', '.js', '.png', '.jpg', '.gif', '.ico']
    if any(request.path.endswith(ext) for ext in static_extensions):
        return

    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    today = datetime.now().date()

    conn = get_db_connection()
    cursor = conn.cursor
    try:
        cursor.execute('''
            INSERT INTO visitor_stats (ip_address, user_agent, visit_date)
            VALUES (%s, %s, %s)
        ''', (ip_address, user_agent, today))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        pass
    finally:
        conn.close()

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
            cursor = conn.cursor
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                           (username, generate_password_hash(password)))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash(f'Username "%s" is already taken.' % username, 'error')
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
        user = conn.execute('SELECT * FROM users WHERE username = %s', (username,)).fetchone()
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
    cursor = conn.cursor

    cursor.execute('SELECT DISTINCT book_name FROM words ORDER BY book_name ASC')
    book_names = [row['book_name'] for row in cursor.fetchall()]

    if session.get('is_admin'):
        page = request.args.get('page', 1, type=int)
        per_page = 50
        book_filter = request.args.get('book_name')
        search_query = request.args.get('search', '').strip()

        base_query = 'FROM words'
        conditions = []
        params = []

        if book_filter:
            conditions.append('book_name = %s')
            params.append(book_filter)
        
        if search_query:
            conditions.append('(english_word LIKE %s OR vocalized_arabic LIKE %s)')
            params.extend([f'%%{search_query}%%', f'%%{search_query}%%'])

        where_clause = ''
        if conditions:
            where_clause = ' WHERE ' + ' AND '.join(conditions)

        query = 'SELECT * ' + base_query + where_clause
        count_query = 'SELECT COUNT(*) AS count ' + base_query + where_clause

        total_words = cursor.execute(count_query, tuple(params)).fetchone()['count']
        total_pages = (total_words + per_page - 1) // per_page

        query += ' ORDER BY english_word ASC LIMIT %s OFFSET %s'
        params.extend([per_page, (page - 1) * per_page])

        cursor.execute(query, tuple(params))
        words = cursor.fetchall()
        conn.close()
        return render_template('index.html', words=words, book_names=book_names, 
                               selected_book=book_filter, current_page=page, 
                               total_pages=total_pages, search_query=search_query)
    else:
        user_id = session['user_id']

        # Get book statistics (name and count of words to review)
        query = """
            SELECT 
                w.book_name,
                COUNT(w.id) AS words_to_review
            FROM words w
            LEFT JOIN user_word_progress p ON w.id = p.word_id AND p.user_id = %s
            WHERE p.word_id IS NULL OR p.next_review <= CURRENT_DATE
            GROUP BY w.book_name
            ORDER BY w.book_name ASC;
        """
        cursor.execute(query, (user_id,))
        books_with_counts = cursor.fetchall()

        # Also get the total counts for the "All Books" buttons
        new_words_query = "SELECT COUNT(w.id) AS count FROM words w LEFT JOIN user_word_progress p ON w.id = p.word_id AND p.user_id = %s WHERE p.word_id IS NULL"
        due_words_query = "SELECT COUNT(p.word_id) AS count FROM user_word_progress p JOIN words w ON p.word_id = w.id WHERE p.user_id = %s AND p.next_review <= CURRENT_DATE"
        
        new_words_count = cursor.execute(new_words_query, (user_id,)).fetchone()['count']
        due_words_count = cursor.execute(due_words_query, (user_id,)).fetchone()['count']

        conn.close()
        return render_template('index.html', 
                               books_with_counts=books_with_counts,
                               new_words_count=new_words_count,
                               due_words_count=due_words_count)

@app.route('/import_csv', methods=['GET', 'POST'])
def import_words_from_csv():
    """
    Page for admins to import words from separate CSV files.
    - To add new words, provide 'English' and 'Arabic' files. 'Synonyms' is optional.
    - To update synonyms, provide only the 'Synonyms' file. 
      This file must contain two columns: the English word to identify the record, 
      and the new synonyms.
    """
    if not session.get('is_admin'):
        flash('You must be an admin to import words.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        english_file = request.files.get('english_file')
        arabic_file = request.files.get('arabic_file')
        synonyms_file = request.files.get('synonyms_file')
        reset_database = request.form.get('reset_database') == 'on'

        # --- File Handling ---
        files_present = {
            'english': english_file and english_file.filename,
            'arabic': arabic_file and arabic_file.filename,
            'synonyms': synonyms_file and synonyms_file.filename
        }

        # Determine the operation type
        is_new_word_operation = files_present['english'] and files_present['arabic']
        is_synonym_update_operation = files_present['synonyms'] and not files_present['english'] and not files_present['arabic']

        if not is_new_word_operation and not is_synonym_update_operation:
            flash('Invalid file combination. To add new words, upload English and Arabic files. To update synonyms, upload only the Synonyms file.', 'error')
            return redirect(request.url)

        conn = get_db_connection()
        cursor = conn.cursor

        try:
            if reset_database:
                conn.close()
                # Re-establish connection and reset
                conn = get_db_connection()
                cursor = conn.cursor
                cursor.execute("DROP TABLE IF EXISTS user_word_progress")
                cursor.execute("DROP TABLE IF EXISTS words")
                conn.commit()
                create_words_table(cursor)
                create_user_word_progress_table(cursor)
                conn.commit()
                flash('Database has been reset.', 'warning')

            # --- Scenario 1: Add New Words ---
            if is_new_word_operation:
                # Secure filenames and save
                english_filename = secure_filename(english_file.filename)
                arabic_filename = secure_filename(arabic_file.filename)
                english_filepath = os.path.join(app.config['UPLOAD_FOLDER'], english_filename)
                arabic_filepath = os.path.join(app.config['UPLOAD_FOLDER'], arabic_filename)
                english_file.save(english_filepath)
                arabic_file.save(arabic_filepath)

                synonyms_filepath = None
                if files_present['synonyms']:
                    synonyms_filename = secure_filename(synonyms_file.filename)
                    synonyms_filepath = os.path.join(app.config['UPLOAD_FOLDER'], synonyms_filename)
                    synonyms_file.save(synonyms_filepath)

                # Read data from files
                with open(english_filepath, mode='r', encoding='utf-8') as ef:
                    english_words = [row[0].strip() for row in csv.reader(ef) if row]
                with open(arabic_filepath, mode='r', encoding='utf-8') as af:
                    arabic_translations = [row[0].strip() for row in csv.reader(af) if row]
                
                synonyms_list = []
                if synonyms_filepath:
                    with open(synonyms_filepath, mode='r', encoding='utf-8') as sf:
                        synonyms_list = [
                            ','.join(cell.strip().replace(';', ',') for cell in row if cell.strip()) if row else ''
                            for row in csv.reader(sf)
                        ]

                # Process the data
                added_count, skipped_count = 0, 0
                
                min_length = min(len(english_words), len(arabic_translations), len(synonyms_list) if synonyms_list else len(english_words))
                
                for i in range(min_length):
                    english_word = english_words[i]
                    vocalized_arabic = arabic_translations[i]
                    synonyms = synonyms_list[i] if i < len(synonyms_list) else ''
                    
                    if not english_word or not vocalized_arabic:
                        skipped_count += 1
                        continue
                    
                    book_name = f'Book {(i // 600) + 1}'

                    cursor.execute("""
                        INSERT INTO words (english_word, vocalized_arabic, alternative_translations, book_name) 
                        VALUES (%s, %s, %s, %s)
                    """, (english_word, vocalized_arabic, synonyms, book_name))
                    added_count += 1
                
                conn.commit()
                flash(f'Import complete: {added_count} added, {skipped_count} skipped.', 'success')

            # --- Scenario 2: Update Synonyms ---
            elif is_synonym_update_operation:
                synonyms_filename = secure_filename(synonyms_file.filename)
                synonyms_filepath = os.path.join(app.config['UPLOAD_FOLDER'], synonyms_filename)
                synonyms_file.save(synonyms_filepath)

                updated_count, not_found_count = 0, 0
                with open(synonyms_filepath, mode='r', encoding='utf-8') as sf:
                    reader = csv.reader(sf)
                    for row in reader:
                        if len(row) < 2: continue
                        english_word = row[0].strip()
                        synonyms_list = []
                        for s in row[1:]:
                            s_stripped = s.strip()
                            if s_stripped:
                                synonyms_list.append(s_stripped.replace(';', ','))
                        
                        if not synonyms_list: continue

                        synonyms = ','.join(synonyms_list)
                        
                        cursor.execute("SELECT id FROM words WHERE english_word = %s", (english_word,))
                        word_record = cursor.fetchone()
                        
                        if word_record:
                            cursor.execute("UPDATE words SET alternative_translations = %s WHERE id = %s", (synonyms, word_record['id']))
                            updated_count += 1
                        else:
                            not_found_count += 1
                
                conn.commit()
                flash(f'Synonym update complete: {updated_count} words updated, {not_found_count} words not found.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'An error occurred: {e}', 'error')
        finally:
            conn.close()
            for f in [english_file, arabic_file, synonyms_file]:
                if f and f.filename:
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
                    if os.path.exists(filepath):
                        os.remove(filepath)

        return redirect(url_for('index'))
        
    return render_template('import_csv.html')

@app.route('/review')
def review():
    """Shows a word for the user to review based on their personal progress."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    book_filter = request.args.get('book_name')
    review_type = request.args.get('review_type')

    conn = get_db_connection()
    cursor = conn.cursor

    cursor.execute('SELECT DISTINCT book_name FROM words ORDER BY book_name ASC')
    book_names = [row['book_name'] for row in cursor.fetchall()]

    base_query = """
        SELECT w.id, w.english_word, w.vocalized_arabic, w.book_name
        FROM words w
        LEFT JOIN user_word_progress p ON w.id = p.word_id AND p.user_id = %s
    """
    params = [user_id]
    
    if review_type == 'new':
        base_query += ' WHERE p.word_id IS NULL'
    elif review_type == 'due':
        base_query += " WHERE p.next_review <= CURRENT_DATE"
    else:
        base_query += " WHERE (p.next_review <= CURRENT_DATE OR p.word_id IS NULL)"

    if book_filter:
        base_query += ' AND w.book_name = %s'
        params.append(book_filter)

    if review_type is None:
        order_clause = ' ORDER BY CASE WHEN p.word_id IS NULL THEN 1 ELSE 0 END, p.next_review ASC, RANDOM()'
    else:
        order_clause = ' ORDER BY RANDOM()'

    query = base_query + order_clause + ' LIMIT 1'
    
    word_data = cursor.execute(query, tuple(params)).fetchone()
    conn.close()

    if not word_data:
        flash('No more words to review in this category for now!', 'success')
        return redirect(url_for('index', book_name=book_filter if book_filter else ''))

    return render_template('review.html', word=dict(word_data), book_names=book_names, selected_book=book_filter)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    """Processes a review and updates the user's personal progress using a robust SM-2 algorithm."""
    print("\n--- [START] ---")
    print("--- 1. Authorization and Input Validation ---")
    if 'user_id' not in session:
        print("ERROR: No user_id in session. Aborting.")
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    user_id = session['user_id']
    data = request.get_json()
    word_id = data.get('word_id')
    user_input = data.get('user_input', '').strip().lower()

    print(f"Review Submission Details: UserID={user_id}, WordID={word_id}, Input='{user_input}'")

    if not all([word_id, isinstance(word_id, int)]):
        print(f"ERROR: Invalid input. WordID is missing or not an integer. Data: {data}")
        return jsonify({'success': False, 'message': 'Invalid input'}), 400

    print("--- 2. Database Fetch ---")
    conn = get_db_connection()
    cursor = conn.cursor
    print("Database connection established.")

    word_info = cursor.execute('SELECT english_word, alternative_translations, example_en FROM words WHERE id = %s', (word_id,)).fetchone()
    if not word_info:
        print(f"ERROR: Word with ID {word_id} not found.")
        conn.close()
        return jsonify({'success': False, 'message': 'Word not found'}), 404
    
    print(f"Word Info Found: English='{word_info['english_word']}', Alternatives='{word_info['alternative_translations']}'")

    progress = cursor.execute('SELECT * FROM user_word_progress WHERE user_id = %s AND word_id = %s', (user_id, word_id)).fetchone()
    if progress:
        print(f"Existing progress found: Reps={progress['repetitions']}, Ease={progress['ease_factor']:.2f}, Interval={progress['interval_days']} days")
    else:
        print("No existing progress for this word. This is a NEW word for this user.")

    print("--- 3. Answer Evaluation ---")
    is_correct = False
    correct_answer_type = 'incorrect'
    primary_answer = word_info['english_word'].strip().lower()
    
    print(f"User Input: '{user_input}', Primary Answer: '{primary_answer}'")
    if user_input == primary_answer:
        is_correct = True
        correct_answer_type = 'correct'
        print("RESULT: CORRECT (Primary match)")
    else:
        alternatives = word_info['alternative_translations']
        if alternatives:
            alt_list = [alt.strip().lower() for alt in alternatives.split(',')]
            print(f"Checking against alternatives: {alt_list}")
            if user_input in alt_list:
                is_correct = True
                correct_answer_type = 'alternative'
                print("RESULT: CORRECT (Alternative match)")
        else:
            print("No alternatives to check against.")

    if not is_correct:
        print("RESULT: INCORRECT")

    print("--- 4. SM-2 Algorithm Calculation ---")
    quality = 5 if is_correct else 0
    ease_factor = progress['ease_factor'] if progress else 2.5
    repetitions = progress['repetitions'] if progress else 0
    interval_days = progress['interval_days'] if progress else 1
    print(f"SRS Input: Quality={quality}, OldEase={ease_factor:.2f}, OldReps={repetitions}, OldInterval={interval_days}")

    new_ease_factor = max(1.3, ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

    if is_correct:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = max(1, int(round(interval_days * new_ease_factor)))
    else:
        new_repetitions = 0
        new_interval = 1
    
    print(f"SRS Output: NewEase={new_ease_factor:.4f}, NewReps={new_repetitions}, NewInterval={new_interval}")

    print("--- 5. Session State Update ---")
    session.setdefault('reviewed_word_ids', [])
    session.setdefault('correct_word_ids', [])
    session.setdefault('incorrect_word_ids', [])
    print(f"Session state BEFORE: Correct={session.get('correct_word_ids')}, Incorrect={session.get('incorrect_word_ids')}")

    if word_id not in session['reviewed_word_ids']:
        session['reviewed_word_ids'].append(word_id)

    if is_correct:
        if word_id not in session['correct_word_ids']:
            session['correct_word_ids'].append(word_id)
        if word_id in session['incorrect_word_ids']:
            session['incorrect_word_ids'].remove(word_id)
    else:
        if word_id not in session['incorrect_word_ids']:
            session['incorrect_word_ids'].append(word_id)
        if word_id in session['correct_word_ids']:
            session['correct_word_ids'].remove(word_id)

    session.modified = True
    print(f"Session state AFTER: Correct={session.get('correct_word_ids')}, Incorrect={session.get('incorrect_word_ids')}")

    print("--- 6. Database Update ---")
    today = datetime.now().date()
    new_next_review = today + timedelta(days=new_interval)
    print(f"Updating database. Next review date: {new_next_review.isoformat()}")

    if progress:
        cursor.execute('''
            UPDATE user_word_progress
            SET last_reviewed = %s, next_review = %s, repetitions = %s, ease_factor = %s, interval_days = %s
            WHERE user_id = %s AND word_id = %s
        ''', (today.isoformat(), new_next_review.isoformat(), new_repetitions, new_ease_factor, new_interval, user_id, word_id))
        print("DB command: UPDATE user_word_progress.")
    else:
        cursor.execute('''
            INSERT INTO user_word_progress (user_id, word_id, last_reviewed, next_review, repetitions, ease_factor, interval_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, word_id, today.isoformat(), new_next_review.isoformat(), new_repetitions, new_ease_factor, new_interval))
        print("DB command: INSERT INTO user_word_progress.")

    conn.commit()
    conn.close()
    print("Database transaction committed and connection closed.")
    print("--- [END] ---")

    response_data = {
        'success': True,
        'result': correct_answer_type,
        'correct_answer': word_info['english_word'],
        'example_en': word_info['example_en']
    }

    if correct_answer_type == 'correct' and word_info['alternative_translations']:
        response_data['show_alternatives'] = word_info['alternative_translations']

    return jsonify(response_data)

@app.route('/session_summary')
def session_summary():
    """Displays a summary of the current review session."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    correct_count = len(session.get('correct_word_ids', []))
    incorrect_count = len(session.get('incorrect_word_ids', []))
    total_words_reviewed = len(session.get('reviewed_word_ids', []))

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
    cursor = conn.cursor

    # Total words reviewed by the user
    cursor.execute('''
        SELECT COUNT(*) AS count FROM user_word_progress WHERE user_id = %s
    ''', (user_id,))
    total_reviewed_words = cursor.fetchone()['count']

    # Words due for review today
    cursor.execute('''
        SELECT COUNT(*) AS count FROM user_word_progress
        WHERE user_id = %s AND next_review <= CURRENT_DATE
    ''', (user_id,))
    words_due_today = cursor.fetchone()['count']

    # Words mastered (repetitions >= 5)
    cursor.execute('''
        SELECT COUNT(*) AS count FROM user_word_progress
        WHERE user_id = %s AND repetitions >= 5
    ''', (user_id,))
    words_mastered = cursor.fetchone()['count']

    # Average ease factor
    cursor.execute('''
        SELECT AVG(ease_factor) AS ease FROM user_word_progress WHERE user_id = %s
    ''', (user_id,))
    avg_ease_factor = cursor.fetchone()['ease']
    if avg_ease_factor is None:
        avg_ease_factor = 0.0

    conn.close()

    return render_template('statistics.html',
                           total_reviewed_words=total_reviewed_words,
                           words_due_today=words_due_today,
                           words_mastered=words_mastered,
                           avg_ease_factor=f'{avg_ease_factor:.2f}')

@app.route('/word_list')
def word_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    list_type = request.args.get('list_type')

    conn = get_db_connection()
    cursor = conn.cursor

    words = []
    title = "Word List"

    if list_type == 'reviewed':
        title = "Total Words Reviewed"
        cursor.execute('''
            SELECT w.id, w.english_word, w.vocalized_arabic, w.alternative_translations, p.next_review
            FROM words w
            JOIN user_word_progress p ON w.id = p.word_id
            WHERE p.user_id = %s
            ORDER BY w.english_word
        ''', (user_id,))
        words = cursor.fetchall()
    elif list_type == 'due_today':
        title = "Words Due for Review Today"
        cursor.execute('''
            SELECT w.id, w.english_word, w.vocalized_arabic, w.alternative_translations, p.next_review
            FROM words w
            JOIN user_word_progress p ON w.id = p.word_id
            WHERE p.user_id = %s AND p.next_review <= CURRENT_DATE
            ORDER BY w.english_word
        ''', (user_id,))
        words = cursor.fetchall()
    elif list_type == 'mastered':
        title = "Words Mastered"
        cursor.execute('''
            SELECT w.id, w.english_word, w.vocalized_arabic, w.alternative_translations, p.next_review
            FROM words w
            JOIN user_word_progress p ON w.id = p.word_id
            WHERE p.user_id = %s AND p.repetitions >= 5
            ORDER BY w.english_word
        ''', (user_id,))
        words = cursor.fetchall()
    else:
        flash('Invalid list type.', 'error')
        conn.close()
        return redirect(url_for('statistics'))

    conn.close()
    return render_template('word_list.html', words=words, title=title)

@app.route('/session_word_list')
def session_word_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    list_type = request.args.get('list_type')
    word_ids = []
    title = "Session Word List"

    if list_type == 'reviewed':
        title = "Words Reviewed in This Session"
        word_ids = session.get('reviewed_word_ids', [])
    elif list_type == 'correct':
        title = "Correct Answers in This Session"
        word_ids = session.get('correct_word_ids', [])
    elif list_type == 'incorrect':
        title = "Incorrect Answers in This Session"
        word_ids = session.get('incorrect_word_ids', [])
    else:
        flash('Invalid list type.', 'error')
        return redirect(url_for('session_summary'))

    words = []
    if word_ids:
        conn = get_db_connection()
        placeholders = ','.join('%s' for _ in word_ids)
        query = f'''
            SELECT w.id, w.english_word, w.vocalized_arabic, w.alternative_translations, p.next_review
            FROM words w
            LEFT JOIN user_word_progress p ON w.id = p.word_id AND p.user_id = %s
            WHERE w.id IN ({placeholders})
            ORDER BY w.english_word
        '''
        params = [session['user_id']] + word_ids
        words = conn.execute(query, params).fetchall()
        conn.close()
    
    return render_template('word_list.html', words=words, title=title)

@app.route('/reset_session')
def reset_session():
    """Resets the current review session statistics."""
    session['correct_answers'] = 0
    session['incorrect_answers'] = 0
    session['reviewed_word_ids'] = []
    session['correct_word_ids'] = []
    session['incorrect_word_ids'] = []
    session.modified = True
    flash('Review session statistics have been reset.', 'info')
    return redirect(url_for('review'))

@app.route('/edit_word/<int:word_id>', methods=['GET', 'POST'])
def edit_word(word_id):
    if not session.get('is_admin'):
        flash('You must be an admin to edit words.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        english_word = clean_string(request.form['english_word'])
        vocalized_arabic = clean_string(request.form.get('vocalized_arabic', ''))
        alternative_translations = clean_string(request.form.get('alternative_translations', '')).replace(';', ',')
        book_name = clean_string(request.form.get('book_name', 'Uncategorized'))

        current_word = conn.execute('SELECT * FROM words WHERE id = %s', (word_id,)).fetchone()
        if not current_word:
            flash('Word not found.', 'error')
            conn.close()
            return redirect(url_for('index'))

        is_valid_eng, eng_error = is_valid_word(english_word)
        if not is_valid_eng:
            flash(f'English word invalid: {eng_error}', 'error')
            conn.close()
            return render_template('edit_word.html', word=current_word)

        is_valid_ara, ara_error = is_valid_word(vocalized_arabic)
        if not is_valid_ara:
            flash(f'Arabic translation invalid: {ara_error}', 'error')
            conn.close()
            return render_template('edit_word.html', word=current_word)
        
        is_valid_book, book_error = is_valid_book_name(book_name)
        if not is_valid_book:
            flash(f'Book name invalid: {book_error}', 'error')
            conn.close()
            return render_template('edit_word.html', word=current_word)

        try:
            conn.execute('''
                UPDATE words
                SET english_word = %s, vocalized_arabic = %s, alternative_translations = %s, book_name = %s
                WHERE id = %s
            ''', (english_word, vocalized_arabic, alternative_translations, book_name, word_id))
            conn.commit()
            flash('Word updated successfully!', 'success')
            return redirect(url_for('index'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash(f'The English word "%s" already exists.' % english_word, 'error')
            conn.close()
            return render_template('edit_word.html', word=current_word)
        except Exception as e:
            flash(f'An unexpected error occurred: {e}', 'error')
            conn.close()
            return render_template('edit_word.html', word=current_word)
        finally:
            pass
    
    word = conn.execute('SELECT * FROM words WHERE id = %s', (word_id,)).fetchone()
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
    conn.execute('DELETE FROM words WHERE id = %s', (word_id,))
    conn.commit()
    conn.close()
    flash('Word deleted successfully!', 'success')
    return redirect(url_for('index'))

# Admin panel and user management routes
@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor

    users = cursor.execute('SELECT id, username, is_admin FROM users ORDER BY username ASC').fetchall()

    page = request.args.get('page', 1, type=int)
    per_page = 50

    total_words = cursor.execute('SELECT COUNT(*) AS count FROM words').fetchone()['count']
    total_pages = (total_words + per_page - 1) // per_page

    offset = (page - 1) * per_page
    words = cursor.execute('SELECT * FROM words ORDER BY english_word ASC LIMIT %s OFFSET %s', (per_page, offset)).fetchall()
    
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
    conn.execute('UPDATE users SET is_admin = 1 WHERE id = %s', (user_id,))
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
    conn.execute('DELETE FROM users WHERE id = %s', (user_id,))
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
        placeholders = ','.join('%s' for _ in word_ids_to_delete)
        query = f'DELETE FROM words WHERE id IN ({placeholders})'
        conn.execute(query, word_ids_to_delete)
        conn.commit()
        flash(f'{len(word_ids_to_delete)} words have been successfully deleted.', 'success')
    except Exception as e:
        flash(f'An error occurred: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_panel'))


@app.route('/admin/visitor_stats')
def admin_visitor_stats():
    if not session.get('is_admin'):
        flash('You must be an admin to view this page.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor

    today = datetime.now().date()
    cursor.execute("SELECT COUNT(DISTINCT ip_address) AS count FROM visitor_stats WHERE visit_date = %s", (today,))
    daily_visitors = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(DISTINCT ip_address) AS count FROM visitor_stats")
    total_visitors = cursor.fetchone()['count']

    conn.close()

    return render_template('admin_visitor_stats.html', daily_visitors=daily_visitors, total_visitors=total_visitors)


import click
from flask.cli import with_appcontext

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=True)
