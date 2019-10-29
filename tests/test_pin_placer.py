import os, pathlib
from verilog_pin_extract import VerilogModule
# from verilog2phy import *
from pin_placer import *
from LEFBuilder import LEFBuilder
from GDSBuilder import GDSDesign
from libraries.bbox_libs import *

projects_dir = pathlib.Path(__file__).parents[2]
test_techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
test_techfile = str(test_techfile)
asap7_layermapfile = projects_dir / 'phyrilog/resources/asap7_TechLib.layermap'

pin_specs = {'pins': {'h_layer': "M4",
                      'v_layer': "M5",
                      'pin_length': 1,
                      'output_side': 'right',
                      # 'carry':{'center': 1.5,
                      #          'side': 'bottom'}
                      },
             'pg_pins': {'h_layer': "M4",
                         'v_layer': "M5",
                         'strap_orientation': 'horizontal',
                         'pwr_pin': {  # 'layer': 'M3',
                             'center': None,
                             'side': 'top'},
                         'gnd_pin': {  # 'layer': 'M3',
                             'center': None,
                             'side': 'top'}}
             }

options = {'pg_pin_placement': 'small_pins'}

spec_dict = {'pin_margin': True,
             'aspect_ratio': [0.625, 1],
             'interlace_interval': 5,
             # 'strap_spacing': 0.092,
             'interlace_orientation': 'horizontal',
             # 'y_width': 12.5,
             'site': 'coreSite',
             'output_side': 'left',
             'exclude_layers': ['M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'Pad']}

spec_dict = r_update(spec_dict, pin_specs)
spec_dict = r_update(spec_dict, options)

if __name__ == '__main__':
    test_mod = VerilogModule('TestParamsAndPorts', filename=projects_dir / 'phyrilog/tests/test_module.v')
    # test_pin_placer = PinPlacer(test_mod.pins, test_mod.power_pins, test_techfile, pin_specs=pin_specs,
    #                             options_dict=options)
    # test_pin_placer._sort_pins_by_side()
    # test_pin_placer.autodefine_boundaries()
    # test_pin_placer._place_defined_pins()
    # test_pin_placer.place_interlaced_pg_pins('M4', 3, [test_pin_placer.specs['internal_box'][1],
    #                                                    test_pin_placer.specs['internal_box'][3]])
    # test_pin_placer._make_subpartitions()
    # test_pin_placer.place_free_pins()
    test_bbox = BBoxPHY(test_mod, test_techfile, spec_dict=spec_dict)
    test_bbox.place_pins()
    test_lef = BBoxLEFBuilder(test_bbox)
    test_gds = GDSDesign(test_bbox, layermap_file=asap7_layermapfile)
    test_gds.add_polygons()
    test_lef.write_lef(projects_dir / 'phyrilog/tests/test.lef')
    test_gds.write_gdsfile(projects_dir / 'phyrilog/tests/test.gds')
    5
