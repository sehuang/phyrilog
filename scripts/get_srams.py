import re

class SRAMList:
    """This just has a list of srams."""

    def __init__(self, file, listfile=None):
        self.everything = []
        self.srams = []
        if listfile:
            with open(listfile) as f:
                for line in listfile:
                    self.srams.append(line)
        else:
            with open(file) as f:
                for line in f:
                    if line:
                        words = line.split()
                        if len(words) > 0:
                            if words[0] == 'module':
                               self.everything.append(words[1])
            pattern = re.compile('_1bit')
            for sram in self.everything:
                if not re.search(pattern,sram):
                    self.srams.append(sram)

    def search(self, pattern):
        self.srams = []
        pttrn = re.compile(pattern)
        for sram in self.everything:
            if re.search(pttrn, sram):
                self.srams.append(sram)
