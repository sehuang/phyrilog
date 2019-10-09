import os, pathlib
from verilog_pin_extract import VerilogModule
from verilog2phy import *
from pin_placer import *

projects_dir = pathlib.Path(__file__).parents[2]
test_techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
test_techfile = str(test_techfile)
asap7_layermapfile = projects_dir / 'phyrilog/asap7_TechLib.layermap'

pin_specs = {'pins': {'h_layer': "M2",
                      'v_layer': "M3",
                      'pin_length': 1
                      },
             'pg_pins': {'h_layer': "M2",
                         'v_layer': "M3",
                         'pwr_pin': {'layer': 'M3',
                                     'center': None,
                                     'side': 'top'},
                         'gnd_pin': {'layer': 'M3',
                                     'center': None,
                                     'side': 'top'}}
             }


if __name__ == '__main__':
    test_mod = VerilogModule('TestParamsAndPorts', filename=projects_dir / 'phyrilog/tests/test_module.v')
    test_pin_placer = PinPlacer(test_mod.pins, test_mod.power_pins, test_techfile, pin_specs=pin_specs)
    test_pin_placer._sort_pins_by_side()
    test_pin_placer._autodefine_boundaries()
    test_pin_placer._place_defined_pins()
    5