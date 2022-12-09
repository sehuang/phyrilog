import os
import sys
import pathlib
import re
import gc
import pickle

aratios ={}

with open('scrapeout.pickle', 'rb') as f:
    sizes = pickle.load(f)

for name, size in sizes.items():
    aratios[name] = float(size['y']) / float(size['x'])

print(aratios)