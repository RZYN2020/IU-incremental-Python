import sys 
import os

if __name__ == 'main':
    dir = os.path.dirname(__file__) + sys.argv[1]
    name = sys.argv[2]
    file_extentions = ['.in', '.py', '.golden']
    for ext in file_extentions:
        os.mkdir(dir + '/' + name + ext)