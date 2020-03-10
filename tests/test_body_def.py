from verilog_pin_extract import *
import pathlib
import os
import pprint

if __name__ == '__main__':
    this_path = os.path.abspath('')
    projects_dir = pathlib.Path(this_path).parents[1]
    behav_model = projects_dir / 'phyrilog/views/behavioral/sram.v'
    # behav_model = projects_dir / 'phyrilog/src/sram_behav_models.v'
    consts = projects_dir / 'phyrilog/views2/behavioral/const.vh'
    asap7_layermapfile = projects_dir / 'phyrilog/asap7_TechLib.layermap'
    techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
    corners = projects_dir / 'phyrilog/resources/asap7_lib_corners.json'

    sram = VerilogModule("SRAM1RW1024x8", filename=behav_model, clocks=('clock'), seq_pins=[])
    pprint.pprint(sram.ports_json_dict)
    pprint.pprint(sram.pin_names)