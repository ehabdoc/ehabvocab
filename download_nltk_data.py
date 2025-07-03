import nltk

try:
    nltk.data.find('corpora/wordnet.zip')
    print("WordNet is already downloaded.")
except nltk.downloader.DownloadError:
    print("Downloading WordNet...")
    nltk.download('wordnet')
    print("WordNet downloaded successfully.")

try:
    nltk.data.find('tokenizers/punkt.zip')
    print("Punkt is already downloaded.")
except nltk.downloader.DownloadError:
    print("Downloading Punkt...")
    nltk.download('punkt')
    print("Punkt downloaded successfully.")

try:
    # NLTK's lemmatizer uses the 'omw-1.4' resource which contains WordNet data in multiple languages
    nltk.data.find('corpora/omw-1.4.zip')
    print("OMW-1.4 (for lemmatizer) is already downloaded.")
except nltk.downloader.DownloadError:
    print("Downloading OMW-1.4...")
    nltk.download('omw-1.4')
    print("OMW-1.4 downloaded successfully.")
