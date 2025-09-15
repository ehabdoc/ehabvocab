import csv
import requests
import os
import time
import getpass

# --- CONFIGURATION ---
# IMPORTANT: Replace "YOUR_API_KEY" with your actual Merriam-Webster Thesaurus API key.
# You can get a free key from: https://dictionaryapi.com/register-your-app
API_KEY = os.environ.get("MERRIAM_WEBSTER_API_KEY")
if not API_KEY:
    API_KEY = getpass.getpass("Enter your Merriam-Webster API key: ")
API_URL = "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{word}?key={key}"
INPUT_CSV = "words_with_synonyms.csv"
OUTPUT_CSV = "words_with_new_synonyms.csv"
MAX_SYNONYMS = 3
# The API has a rate limit, so we add a small delay between requests.
REQUEST_DELAY_SECONDS = 0.5

def get_synonyms(word):
    """
    Fetches and selects the best synonyms for a word from the Merriam-Webster API.
    """
    if not API_KEY or API_KEY == "YOUR_API_KEY":
        print("ERROR: Merriam-Webster API key is not set.")
        print("Please get a free key from https://dictionaryapi.com/register-your-app")
        print("And set it as an environment variable 'MERRIAM_WEBSTER_API_KEY' or directly in this script.")
        return None

    try:
        response = requests.get(API_URL.format(word=word.lower(), key=API_KEY))
        response.raise_for_status()
        data = response.json()

        if not data or not isinstance(data, list):
            print(f"  - No synonyms found for '{word}'.")
            return []

        # The API can return multiple entries for a word, sometimes with different meanings.
        # We will look for the entry that is an exact match for the word.
        for entry in data:
            if isinstance(entry, dict) and entry.get('hwi', {}).get('hw', '').lower() == word.lower():
                # Found an exact match, let's get its synonyms.
                syns = entry.get("meta", {}).get("syns", [])
                if syns:
                    # The synonyms are in nested lists, flatten them.
                    flat_syns = [s for sublist in syns for s in sublist]
                    # Return the top synonyms, up to the configured max.
                    return flat_syns[:MAX_SYNONYMS]

        # If no exact match was found, try to use the first entry's synonyms as a fallback.
        first_entry = data[0]
        if isinstance(first_entry, dict) and "meta" in first_entry:
            syns = first_entry.get("meta", {}).get("syns", [])
            if syns:
                print(f"  - Note: No exact match for '{word}'. Using synonyms from the first API entry.")
                flat_syns = [s for sublist in syns for s in sublist]
                return flat_syns[:MAX_SYNONYMS]

        print(f"  - Could not parse synonyms for '{word}'.")
        return []

    except requests.exceptions.JSONDecodeError:
        print(f"  - Error: The API response was not valid JSON.")
        print(f"  - API Response Text: {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  - Error fetching synonyms for '{word}': {e}")
        return None
    except (KeyError, IndexError, TypeError) as e:
        print(f"  - Error parsing API response for '{word}': {e}")
        return []

def main():
    """
    Reads words from the input CSV, enriches them with new synonyms,
    and writes the result to the output CSV incrementally.
    """
    print(f"Starting synonym update process...")
    print(f"Input file: {INPUT_CSV}")
    print(f"Output file: {OUTPUT_CSV}")

    try:
        # First, count the total number of words for progress tracking
        with open(INPUT_CSV, mode='r', encoding='utf-8') as infile:
            total_words = sum(1 for row in infile) - 1  # Subtract 1 for the header

        print(f"Found {total_words} words to process.")

        with open(INPUT_CSV, mode='r', encoding='utf-8') as infile, \
             open(OUTPUT_CSV, mode='w', encoding='utf-8', newline='') as outfile:

            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            
            # Ensure 'Synonyms' column exists in the output file
            synonyms_field_name = 'Synonyms'
            if not any(f.lower() == 'synonyms' for f in fieldnames):
                fieldnames.append(synonyms_field_name)

            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for i, row in enumerate(reader):
                # Find the english word column, case-insensitively
                english_word_field = next((f for f in row if f.lower() == 'english_word'), None)

                if not english_word_field:
                    print(f"Skipping row {i+1}: 'English_Word' column not found.")
                    writer.writerow(row) # Write the original row if no word column
                    continue
                
                english_word = row[english_word_field]
                
                if english_word:
                    print(f"Processing word {i+1}/{total_words}: {english_word}")
                    new_synonyms = get_synonyms(english_word)
                    
                    # Find the correct key for synonyms, case-insensitively
                    synonyms_key = next((k for k in row if k.lower() == 'synonyms'), synonyms_field_name)

                    if new_synonyms is not None:
                        row[synonyms_key] = ", ".join(new_synonyms)
                    else:
                        # Keep old synonyms if API call fails
                        print(f"  - API call failed. Keeping existing synonyms for '{english_word}'.")
                
                writer.writerow(row)
                outfile.flush()  # Force Python to write the buffer to the file
                
                # Respect API rate limits
                time.sleep(REQUEST_DELAY_SECONDS)

        print(f"\nProcess complete. Output written to {OUTPUT_CSV}")

    except FileNotFoundError:
        print(f"ERROR: Input file not found at '{INPUT_CSV}'. Please make sure the file exists.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
