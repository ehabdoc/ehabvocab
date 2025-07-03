import re
import unicodedata

def clean_string(input_string):
    """Removes invisible control characters and strips leading/trailing whitespace."""
    if not isinstance(input_string, str):
        return ""
    # Remove control characters (Cc category in Unicode) which are typically invisible
    cleaned_string = "".join(ch for ch in input_string if unicodedata.category(ch)[0] != 'C')
    return cleaned_string.strip()

def is_valid_username(username):
    """
    Validates a username.
    - Must be between 3 and 20 characters.
    - Must contain only letters, numbers, hyphens, underscores, or periods.
    """
    if not (3 <= len(username) <= 20):
        return False, "Username must be between 3 and 20 characters long."
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return False, "Username can only contain letters, numbers, hyphens, underscores, and periods."
    return True, ""

def is_valid_password(password):
    """
    Validates a password.
    - Must be at least 8 characters long.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, ""

def is_valid_word(word):
    """
    Validates a word.
    - Must not be empty.
    - Must not exceed 100 characters.
    - Must not contain HTML tags (< or >).
    """
    if not word:
        return False, "Word cannot be empty."
    if len(word) > 100:
        return False, "Word cannot exceed 100 characters."
    if '<' in word or '>' in word:
        return False, "Word cannot contain HTML tags."
    return True, ""

def is_valid_book_name(book_name):
    """
    Validates a book name.
    - Must not be empty.
    - Must not exceed 100 characters.
    - Must not contain HTML tags (< or >).
    """
    if not book_name:
        return False, "Book name cannot be empty."
    if len(book_name) > 100:
        return False, "Book name cannot exceed 100 characters."
    if '<' in book_name or '>' in book_name:
        return False, "Book name cannot contain HTML tags."
    return True, ""

def is_valid_review_input(user_input):
    """
    Validates the user's input during a review.
    - Must not be empty.
    - Must not exceed 100 characters.
    - Must not contain HTML tags (< or >).
    """
    if not user_input:
        return False, "Input cannot be empty."
    if len(user_input) > 100:
        return False, "Input cannot exceed 100 characters."
    if '<' in user_input or '>' in user_input:
        return False, "Input cannot contain HTML tags."
    return True, ""
