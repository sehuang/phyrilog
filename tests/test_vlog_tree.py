from verilog_pin_extract import *
from verilog_tree_builder import *
from verilog_visitor import *

import os, pathlib

this_path = os.path.abspath('')
projects_dir = pathlib.Path(this_path).parents[1]
behav_model = projects_dir / 'phyrilog/views/behavioral/sram.v'
# behav_model = projects_dir / 'phyrilog/src/sram_behav_models.v'
consts = projects_dir / 'phyrilog/views2/behavioral/const.vh'
asap7_layermapfile = projects_dir / 'phyrilog/asap7_TechLib.layermap'
techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
corners = projects_dir / 'phyrilog/resources/asap7_lib_corners.json'

if __name__ == '__main__':
    test_mod = VerilogModule('SRAM1RW1024x8', filename=behav_model, constfile=consts)
    test_mod.build_tree()
    5