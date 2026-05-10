# ehabvocab — Project Memory

## Session: May 10, 2026

### Done
- Pushed 2 unpushed commits to origin/main
- Fixed 500 error on `/submit_review` — added `example_en` column migration in `create_words_table()` (ALWAYS runs on startup)
- Removed `english_example_sentences.txt` and `seed_examples.py` from `.gitignore` so they deploy to PythonAnywhere
- User ran `git pull` + `python seed_examples.py` + reload on PythonAnywhere → example sentences now show after review

### Feature Suggestions (ranked by effort)

**Quick wins (1-2 edits):**
1. Add a "Still Learning" counter on the review page (shows how many words left in the session)
2. Fix the admin panel — it doesn't use `base.html` and looks inconsistent with the rest of the site

**Medium effort:**
3. Show progress bar during review session (e.g., "5/20 words reviewed")
4. Add an "Add Word" route + page for admins to add single words (template `add_word.html` exists but route doesn't)
5. Keyboard shortcut — press `N` or `Space` to go to next word
6. Sound button — browser speech synthesis for English pronunciation (~3 lines of JS)

**More advanced:**
7. "I knew this" / "I didn't know this" buttons (skip typing, good for mobile)
8. Word search from the index page
9. Mobile-responsive improvements to the review screen

### Orphaned/Dead Files (legacy Arabic UI)
- `templates/vocabulary.html`
- `templates/dashboard.html`
- `templates/ehabvocab.html`
- `templates/summary.html`
- `templates/add_word.html`
- `static/js/script.js`

### Known Minor Issues
- `edit_word.html` has two input fields with `id="vocalized_arabic"` (lines 124 and 127) — second overwrites first on submit
- `admin_panel.html` references `style.css` at wrong path (should be `css/style.css`)
