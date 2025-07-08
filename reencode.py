import codecs

file_path = r'C:\Users\EHAB\Desktop\ehabvocab\words.csv'

# Read with the incorrect encoding
with codecs.open(file_path, 'r', 'latin-1') as f:
    content = f.read()

# Write with the correct encoding
with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)
