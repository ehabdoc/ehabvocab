# AI Prompt for Building a Vocabulary Review Web Application

**Objective:** Create a Python Flask web application for vocabulary review, similar to the 'ehabvocab' project.

**Backend Requirements:**

*   **Framework:** Python with Flask.
*   **Database:** SQLite.
*   **Core Functionality:**
    *   **User Authentication:** Implement registration, login, and logout using secure password handling.
    *   **Vocabulary Management:** Allow users to add, edit, and view words (English, Arabic, synonyms, alternative translations, vocalized Arabic).
    *   **Review System:** Develop a spaced repetition/review system for vocabulary words. Track words due for review, words mastered, etc.
    *   **Statistics:** Provide a dashboard or statistics page showing total reviewed, due today, mastered words, and potentially other metrics.
    *   **CSV Import:** Enable users to import vocabulary lists via CSV files. Ensure secure filename handling.
    *   **Input Validation:** Implement robust server-side validation for all user inputs and file uploads.
*   **Project Structure:**
    *   `app.py`: Main Flask application.
    *   `templates/`: Directory for HTML templates.
    *   `static/`: Directory for CSS, JavaScript, and images.
    *   `validators.py`: Module for input validation logic.
    *   `requirements.txt`: List of Python dependencies.
*   **Security:**
    *   Load secret keys from environment variables.
    *   Use `werkzeug.utils.secure_filename` for uploaded files.

**Frontend Requirements:**

*   **Technology:** Server-rendered HTML, CSS, and JavaScript.
*   **Pages:**
    *   Login page
    *   Registration page
    *   Vocabulary list page (displaying all words)
    *   Review page (presenting words for study)
    *   Session summary page
    *   Statistics page
    *   Import CSV page
    *   Admin panel (optional, for managing words/users)
*   **UI/UX:**
    *   Clean, modern design.
    *   Responsive for different screen sizes.
    *   User-friendly navigation.
    *   Interactive elements where appropriate (e.g., clickable list items, hover effects).

**Deliverables:**
A complete, runnable Flask application that meets the above requirements.
