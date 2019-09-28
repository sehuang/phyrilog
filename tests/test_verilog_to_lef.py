from verilog_pin_extract import VerilogModule
from verilog2phy import *
from LEFBuilder import *
from GDSBuilder import GDSDesign
import pprint
import pathlib  # I hate you Microsoft

test_mod = VerilogModule('Memory141', filename='Memory141.v', constfile='const.vh')
test2_mod = VerilogModule('TestParamsAndPorts', filename='test_module.v')
projects_dir = pathlib.Path(__file__).parents[2]
test_techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
test_techfile = str(test_techfile)
asap7_layermapfile = projects_dir / 'phyrilog/asap7_TechLib.layermap'


# test_techfile = "../hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json"

def test_v2lef(spec_dict):
	bbox = BBoxPHY(test2_mod, test_techfile, spec_dict=spec_dict)
	pprint.pprint(test2_mod.pins)
	pprint.pprint(bbox.pins)
	pprint.pprint(bbox.n_inputs)
	pprint.pprint(bbox.n_outputs)
	bbox.define_design_boundaries()
	print(bbox.x_width)
	print(bbox.y_width)
	print(bbox.bbox_x_width)
	print(bbox.bbox_y_width)
	bbox.build_design_repr()
	return bbox

def test_v1lef(spec_dict):
	bbox = BBoxPHY(test2_mod, test_techfile, spec_dict=spec_dict)
	bbox.scale(4)
	bbox_lef = BBoxLEFBuilder(bbox, filename='Memory141.lef', indent_char_width=2)
	pprint.pprint(bbox_lef.blocks)
	bbox_lef.write_lef()

def test_v1gds(spec_dict):
	bbox = BBoxPHY(test2_mod, test_techfile, spec_dict=spec_dict)
	bbox.scale(4)
	bbox_gds = GDSDesign(bbox, layermap_file=asap7_layermapfile)
	bbox_gds.add_polygons()
	bbox_gds.write_gdsfile('Memory141.gds')

if __name__ == '__main__':
	spec_dict = {'pin_margin': True,
				 'site': 'coreSite',
				 'pins': {
					 'h_layer': 'M4',
					 'v_layer': 'M5'
				 },
				 'pg_pins':{
					 'h_layer': 'M8',
					 'v_layer': 'M9',
					 'pwr_pin':{
						 'layer': 'M9',
						 'side': 'top',
						 'center': 1
					 },
					 'gnd_pin':{
						 'layer': 'M9',
						 'side': 'top',
						 'center': 1.2
					 },
				 },
				 'exclude_layers': ['M5']}
	test_v1lef(spec_dict)
	test_v1gds(spec_dict)
	# bbox = test_v2lef(spec_dict)
	# bbox_lef = BBoxLEFBuilder(filename='test_lef.lef', indent_char_width = 2)
	# bbox_lef.make_lef_dict(bbox)
	# print(bbox.pins['sum[0]'].phys_map)
	# pprint.pprint(bbox_lef.blocks)
	# pprint.pprint(bbox_lef.blocks[test2_mod.name].blocks[''].type)
	# bbox_lef.build_lef()
	# print(bbox_lef.lef)
	# bbox_lef.write_lef()
