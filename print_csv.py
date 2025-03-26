import os

for files in os.listdir():
    if files.endswith('.csv'):
        print(files)
        with open(files, 'r') as f:
            print(f.read())