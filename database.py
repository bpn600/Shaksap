import os
import sqlite3
from datetime import datetime
from kivy.utils import platform

LIMBU_DIGITS = {
    '0': '᥆',
    '1': '᥇',
    '2': '᥈',
    '3': '᥉',
    '4': '᥊',
    '5': '᥋',
    '6': '᥌',
    '7': '᥍',
    '8': '᥎',
    '9': '᥏',
}

def get_db_path():
    """Get the correct database path for Android"""
    if platform == 'android':
        from android.storage import app_storage_path
        db_dir = app_storage_path()
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        return os.path.join(db_dir, 'kirat_note.db')
    else:
        return 'kirat_note.db'

def convert_to_limbu_numbers(timestamp):
    """Convert each digit in timestamp to Limbu Unicode"""
    return ''.join(LIMBU_DIGITS.get(char, char) for char in timestamp)

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create folders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created TEXT NOT NULL,
            created_raw TIMESTAMP NOT NULL,
            color TEXT DEFAULT '#2196F3'
        )
    ''')

    # Create notes table with folder_id column
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            created TEXT NOT NULL,
            created_raw TIMESTAMP NOT NULL,
            folder_id INTEGER DEFAULT NULL
        )
    ''')

    # For existing databases, add folder_id column if it doesn't exist
    # This handles database migration for existing installations
    try:
        cursor.execute("SELECT folder_id FROM notes LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        cursor.execute("ALTER TABLE notes ADD COLUMN folder_id INTEGER DEFAULT NULL")
        print("Added folder_id column to existing notes table")

    conn.commit()
    conn.close()

def save_note(content, folder_id=None):
    """Save note content to database with current timestamp in Limbu numbers"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    raw_timestamp = datetime.now()
    formatted_timestamp = raw_timestamp.strftime('%d-%m-%Y | %H:%M:%S')
    limb_timestamp = convert_to_limbu_numbers(formatted_timestamp)
    cursor.execute('''
        INSERT INTO notes (content, created, created_raw, folder_id)
        VALUES (?, ?, ?, ?)
    ''', (content, limb_timestamp, raw_timestamp, folder_id))
    conn.commit()
    conn.close()

def get_all_notes(folder_id=None):
    """Retrieve all notes from database sorted by newest first"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        if not cursor.fetchone():
            return []

        if folder_id is not None:
            # Fixed: Use folder_id parameter correctly
            cursor.execute('SELECT id, content, created FROM notes WHERE folder_id = ? ORDER BY created_raw DESC', (folder_id,))
        else:
            cursor.execute('SELECT id, content, created FROM notes ORDER BY created_raw DESC')
        return cursor.fetchall()
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()

def delete_note(note_id):
    """Delete a note by its ID"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting note: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_note_by_id(note_id):
    """Retrieve a single note by its ID"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, content, created, folder_id FROM notes WHERE id = ?', (note_id,))
        return cursor.fetchone()
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_note_stats():
    """Get statistics about notes - count and total words"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes")
        note_count = cursor.fetchone()[0] or 0
        cursor.execute("SELECT content FROM notes")
        all_notes = cursor.fetchall()
        word_count = 0
        for note in all_notes:
            if note[0]:
                word_count += len(note[0].split())
        return {
            'note_count': note_count,
            'word_count': word_count
        }
    except Exception as e:
        print(f"Error getting note stats: {e}")
        return {'note_count': 0, 'word_count': 0}
    finally:
        if conn:
            conn.close()

def search_words_in_notes(search_term):
    """Search for words in notes that start with the search term"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM notes")
        all_notes = cursor.fetchall()
        matching_words = set()
        for note in all_notes:
            if note[0]:
                words = note[0].split()
                for word in words:
                    if word.startswith(search_term) and len(word) > len(search_term):
                        matching_words.add(word)

        return sorted(list(matching_words))[:5]
    except Exception as e:
        print(f"Error searching words: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Folder Management Functions
def create_folder(folder_name, color='#2196F3'):
    """Create a new folder"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        raw_timestamp = datetime.now()
        formatted_timestamp = raw_timestamp.strftime('%d-%m-%Y | %H:%M:%S')
        limb_timestamp = convert_to_limbu_numbers(formatted_timestamp)

        cursor.execute('''
            INSERT INTO folders (name, created, created_raw, color)
            VALUES (?, ?, ?, ?)
        ''', (folder_name, limb_timestamp, raw_timestamp, color))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        print(f"Folder '{folder_name}' already exists")
        return None
    except Exception as e:
        print(f"Error creating folder: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_folders():
    """Retrieve all folders"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created, color FROM folders ORDER BY name")
        folders = cursor.fetchall()
        return folders
    except Exception as e:
        print(f"Error getting folders: {e}")
        return []
    finally:
        if conn:
            conn.close()

def delete_folder(folder_id):
    """Delete a folder and move its notes to default folder (NULL)"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Move notes to default folder (NULL)
        cursor.execute('UPDATE notes SET folder_id = NULL WHERE folder_id = ?', (folder_id,))

        # Delete the folder
        cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting folder: {e}")
        return False
    finally:
        if conn:
            conn.close()

def update_folder(folder_id, new_name, new_color=None):
    """Update folder details"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if new_color:
            cursor.execute('''
                UPDATE folders SET name = ?, color = ? WHERE id = ?
            ''', (new_name, new_color, folder_id))
        else:
            cursor.execute('''
                UPDATE folders SET name = ? WHERE id = ?
            ''', (new_name, folder_id))

        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Folder name '{new_name}' already exists")
        return False
    except Exception as e:
        print(f"Error updating folder: {e}")
        return False
    finally:
        if conn:
            conn.close()


def get_folder_stats(folder_id):
    """Get statistics for a specific folder"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM notes WHERE folder_id = ?', (folder_id,))
        note_count = cursor.fetchone()[0] or 0
        return note_count
    except Exception as e:
        print(f"Error getting folder stats: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def update_note_folder(note_id, folder_id):
    """Move note to a different folder"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notes SET folder_id = ? WHERE id = ?
        ''', (folder_id, note_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error moving note: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_folder_by_id(folder_id):
    """Get folder by ID"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, created, color FROM folders WHERE id = ?', (folder_id,))
        return cursor.fetchone()
    except Exception as e:
        print(f"Error getting folder: {e}")
        return None
    finally:
        if conn:
            conn.close()

# Add this function to database.py
def get_notes_with_date_grouping(folder_id=None):
    """Retrieve notes with date categories for grouping"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if folder_id is not None:
            cursor.execute('''
                SELECT id, content, created, created_raw, 
                       DATE(created_raw) as note_date
                FROM notes 
                WHERE folder_id = ? 
                ORDER BY created_raw DESC
            ''', (folder_id,))
        else:
            cursor.execute('''
                SELECT id, content, created, created_raw,
                       DATE(created_raw) as note_date
                FROM notes 
                ORDER BY created_raw DESC
            ''')

        notes = cursor.fetchall()

        # Group notes by date category
        from datetime import datetime, timedelta
        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        grouped_notes = {
            'Today': [],
            'Yesterday': [],
            'Previous 7 Days': [],
            'Previous 30 Days': [],
            'Months': {},  # Will store notes by month name
            'Year': {}  # Will store notes by year
        }

        for note in notes:
            note_date = datetime.strptime(note[3], '%Y-%m-%d %H:%M:%S.%f').date() if isinstance(note[3], str) else note[
                3].date()

            if note_date == today:
                grouped_notes['Today'].append(note)
            elif note_date == yesterday:
                grouped_notes['Yesterday'].append(note)
            elif note_date > week_ago:
                grouped_notes['Previous 7 Days'].append(note)
            elif note_date > month_ago:
                grouped_notes['Previous 30 Days'].append(note)
            else:
                # Group by month
                month_name = note_date.strftime('%B %Y')
                if month_name not in grouped_notes['Months']:
                    grouped_notes['Months'][month_name] = []
                grouped_notes['Months'][month_name].append(note)

                # Also group by year for notes older than current year
                year = note_date.strftime('%Y')
                if year not in grouped_notes['Year']:
                    grouped_notes['Year'][year] = []
                grouped_notes['Year'][year].append(note)

        return grouped_notes
    except Exception as e:
        print(f"Error getting grouped notes: {e}")
        return {}
    finally:
        if conn:
            conn.close()