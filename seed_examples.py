import os
import re
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vocab_app.db')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(BASE_DIR, 'english_example_sentences.txt')

def strip_numbering(line):
    return re.sub(r'^\d+\.\s*', '', line).strip()

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(FILE, 'r', encoding='utf-8') as f:
        sentences = [strip_numbering(l) for l in f if l.strip()]

    cursor.execute('SELECT COUNT(*) FROM words')
    total = cursor.fetchone()[0]
    count = min(len(sentences), total)

    for i in range(count):
        word_id = i + 1
        cursor.execute('UPDATE words SET example_en = ? WHERE id = ?', (sentences[i], word_id))

    conn.commit()
    conn.close()
    print(f"Seeded {count} English example sentences (word IDs 1–{count})")

if __name__ == '__main__':
    seed()
