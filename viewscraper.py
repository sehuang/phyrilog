import os
import sys
import pathlib
import re
import gc
import pickle

hammer_sram_dir = pathlib.Path().resolve().parent / 'hammer' / 'src' / 'hammer-vlsi' / 'technology' / 'asap7' / 'sram_compiler' / 'memories'

sizes = {}

name_pattern = re.compile(r'MACRO (\w+)')
size_pattern = re.compile(r'SIZE ([\d\.]+) BY ([\d\.]+)')
site_pattern = re.compile(r'SITE (\w+)')
scale_pattern = re.compile(r'_x(\d+)')

print("Parsing LEF files...")
for path in (hammer_sram_dir / 'lef').glob('*.lef'):
    with open(path, 'r') as f:
        filestr = '\n'.join([line for line in f.readlines()])
        name = re.search(name_pattern, filestr).group(1)
        size = re.search(size_pattern, filestr).group(1, 2)
        site = re.search(site_pattern, filestr).group(1)
        aratio = float(size[1]) / float(size[0])
        try:
            scale = int(re.search(scale_pattern, path.stem).group(1))
        except:
            scale = 1
        print(f"Found {name} with size {size} (aspect ratio: {round(aratio, 4)}) scale {scale}")
        sizes[name] = dict(x_width=float(size[0]), y_width=float(size[1]),
                           aratio=aratio, site=site, scale=scale)
    gc.collect()

with open('predef_sizes.pickle', 'wb') as f:
    pickle.dump(sizes, f)