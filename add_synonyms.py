

import sys
import nltk
from nltk.corpus import wordnet

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
    output_path = input_path.replace('.txt', '_with_synonyms.txt')
    
    with open(input_path, 'r', encoding='utf-8') as f_in, open(output_path, 'w', encoding='utf-8') as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(',', 1)
            if len(parts) != 2:
                continue
                
            english_word, arabic_translation = parts
            synonyms = get_synonyms(english_word)
            
            if not synonyms:
                synonyms_str = english_word
            else:
                synonyms_str = ';'.join(synonyms)
                
            f_out.write(f"{english_word},{arabic_translation},{synonyms_str}\n")
            
    print(f"Processing complete. Output saved to: {output_path}")

if __name__ == "__main__":
    input_file = r"C:\Users\EHAB\ehabvocab\Alternatives (1).txt"
    process_file(input_file)

