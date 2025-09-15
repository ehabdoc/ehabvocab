

import sys
import nltk
from nltk.corpus import wordnet
import csv

def download_nltk_data():
    try:
        nltk.data.find('corpora/wordnet.zip')
    except LookupError:
        nltk.download('wordnet')
    try:
        nltk.data.find('corpora/omw-1.4.zip')
    except LookupError:
        nltk.download('omw-1.4')

def get_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace('_', ' '))
    if word in synonyms:
        synonyms.remove(word)
    return list(synonyms)[:3]

def process_file(input_path):
    download_nltk_data()
    output_path = input_path.replace('.csv', '_with_synonyms.csv')
    
    with open(input_path, 'r', encoding='utf-8') as f_in, open(output_path, 'w', encoding='utf-8', newline='') as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        
        header = next(reader)
        if 'Synonyms' not in header:
            header.append('Synonyms')
        writer.writerow(header)
        
        for row in reader:
            english_word = row[0]
            synonyms = get_synonyms(english_word)
            
            if not synonyms:
                synonyms_str = english_word
            else:
                synonyms_str = ';'.join(synonyms)
                
            if 'Synonyms' in header:
                synonyms_index = header.index('Synonyms')
                if len(row) > synonyms_index:
                    row[synonyms_index] = synonyms_str
                else:
                    row.append(synonyms_str)
            else:
                row.append(synonyms_str)
                
            writer.writerow(row)
            
    print(f"Processing complete. Output saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_synonyms.py <input_file>")
        sys.exit(1)
    input_file = sys.argv[1]
    process_file(input_file)

