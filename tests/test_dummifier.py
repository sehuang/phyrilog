from verilog_pin_extract import *
from dummifier import *
import os, sys, pathlib, pprint

if __name__ == "__main__":
    this_path = os.path.abspath('')
    this_dir = pathlib.Path(this_path)
    testmodulefile = this_dir / 'test_module.v'

    parent = VerilogModule('TestDummifier', filename=testmodulefile, clocks=([]), seq_pins=([]))
    dummifier = Dummifier(parent, macros = ['dummya', 'dummyb'])
    dummifier.scrape_dummies()
    dummifier.get_macro_pins()
    dummifier.get_pin_directions(submod_ins=['ina', 'inb', 'inc'], submod_outs=['outd'])
    pprint.pprint(dummifier.dummy_line_lists)
    pprint.pprint(dummifier.dummy_pin_dicts)
    pprint.pprint(dummifier.dummy_pin_dicts)