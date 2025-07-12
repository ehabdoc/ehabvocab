import csv
import os
import time
import requests
from deep_translator import GoogleTranslator

# --- Configuration ---
home_dir = os.path.expanduser('~')
desktop_path = os.path.join(home_dir, 'Desktop')
input_csv_path = os.path.join(desktop_path, 'ehabvocab', 'words.csv')
output_csv_path = os.path.join(desktop_path, 'words_enriched_sample.csv')
SAMPLE_SIZE = 100

# --- Functions ---

def get_diacritized_arabic(text):
    """
    Uses a free web service (shakkelha.com's API) to add diacritics to Arabic text.
    Returns the diacritized text or the original text if an error occurs.
    """
    try:
        # This is an unofficial endpoint used by the shakkelha.com website
        response = requests.get(f"http://api.shakkelha.com/shakkel/{text}")
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        # The actual diacritized text is returned directly in the response body
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"  - Warning: Could not diacritize '{text}'. Error: {e}")
        return text # Return the original text on failure

def enrich_words_sample():
    """
    Reads a sample of the input CSV, enriches it with diacritics and alternative
    translations via web services, and writes to a new sample CSV on the desktop.
    """
    print(f"Reading from: {input_csv_path}")
    print(f"Will write a sample of {SAMPLE_SIZE} words to: {output_csv_path}")

    if not os.path.exists(input_csv_path):
        print(f"Error: Input file not found at {input_csv_path}")
        return

    translator = GoogleTranslator(source='ar', target='en')
    processed_count = 0

    try:
        with open(input_csv_path, mode='r', encoding='utf-8') as infile, \
             open(output_csv_path, mode='w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            print(f"Starting the enrichment process for the first {SAMPLE_SIZE} words...")

            for i, row in enumerate(reader):
                if i >= SAMPLE_SIZE:
                    print(f"Reached sample limit of {SAMPLE_SIZE}. Stopping.")
                    break
                
                if len(row) < 2:
                    continue

                original_english = row[0].strip().lower()
                arabic_word = row[1].strip()
                
                print(f"Processing word {i+1}/{SAMPLE_SIZE}: '{arabic_word}'")

                # 1. Get Diacritized Arabic
                vocalized_arabic = get_diacritized_arabic(arabic_word)
                
                # 2. Get Alternative English Translations
                all_translations = {original_english}
                try:
                    translation_result = translator.translate(vocalized_arabic) # Use vocalized for better translation
                    if translation_result:
                        all_translations.add(translation_result.strip().lower())
                except Exception as e:
                    print(f"  - Warning: Could not translate '{arabic_word}'. Error: {e}")

                # 3. Combine and Write
                enriched_english = ";".join(sorted(list(all_translations)))
                writer.writerow([enriched_english, vocalized_arabic])
                
                processed_count += 1
                # A polite delay to avoid overwhelming the free services
                time.sleep(1)

        print(f"\nSample enrichment complete!")
        print(f"Successfully processed {processed_count} words.")
        print(f"New sample file created at: {output_csv_path}")

    except FileNotFoundError:
        print(f"Error: Could not open files. Check paths and permissions.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    enrich_words_sample()
