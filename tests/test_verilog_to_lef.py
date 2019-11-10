from verilog_pin_extract import VerilogModule
from verilog2phy import *
from LEFBuilder import *
from GDSBuilder import GDSDesign
import pprint
import pathlib  # I hate you Microsoft

projects_dir = pathlib.Path(__file__).parents[2]
test_techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
test_techfile = str(test_techfile)
asap7_layermapfile = projects_dir / 'phyrilog/asap7_TechLib.layermap'
# test_mod = VerilogModule('Memory141', filename='Memory141.v', constfile='const.vh')
# test2_mod = VerilogModule('TestParamsAndPorts', filename='test_module.v')
test_dco = VerilogModule('ExampleDCO', filename=projects_dir / 'ASAPDCO/views2/behavioral/eagle_dco.v')


# test_techfile = "../hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json"

# def test_v2lef(spec_dict):
# 	bbox = BBoxPHY(test2_mod, test_techfile, spec_dict=spec_dict)
# 	pprint.pprint(test2_mod.pins)
# 	pprint.pprint(bbox.pins)
# 	pprint.pprint(bbox.n_inputs)
# 	pprint.pprint(bbox.n_outputs)
# 	bbox.define_design_boundaries()
# 	print(bbox.x_width)
# 	print(bbox.y_width)
# 	print(bbox.bbox_x_width)
# 	print(bbox.bbox_y_width)
# 	bbox.build_design_repr()
# 	return bbox

def test_v1lef(spec_dict):
	# bbox = BBoxPHY(test_mod, test_techfile, spec_dict=spec_dict)
	bbox = BBoxPHY(test_dco, test_techfile, spec_dict=spec_dict)
	bbox.scale(4)
	bbox_lef = BBoxLEFBuilder(bbox, indent_char_width=2)
	pprint.pprint(bbox_lef.blocks)
	bbox_lef.write_lef('gen_example_dco_x4.lef')

def test_v1gds(spec_dict):
	# bbox = BBoxPHY(test_mod, test_techfile, spec_dict=spec_dict)
	bbox = BBoxPHY(test_dco, test_techfile, spec_dict=spec_dict)
	bbox.scale(4)
	bbox_gds = GDSDesign(bbox, layermap_file=asap7_layermapfile)
	bbox_gds.add_polygons()
	bbox_gds.write_gdsfile('gen_example_dco_x4.gds')

def gen_dco_files(spec_dict):
	dco_bbox = BBoxPHY(test_dco, test_techfile, spec_dict=spec_dict)
	dco_bbox_lef = BBoxLEFBuilder(dco_bbox, indent_char_width=2)
	dco_bbox_gds = GDSDesign(dco_bbox, layermap_file=asap7_layermapfile)
	dco_bbox_gds.add_polygons()
	dco_bbox_lef.write_lef(projects_dir / f'phyrilog/views2/lef/gen_example_dco.lef')
	dco_bbox_gds.write_gdsfile(projects_dir / f'phyrilog/views2/gds/gen_example_dco.gds')

def gen_scaled_dco_files(spec_dict, scale):
	dco_bbox = BBoxPHY(test_dco, test_techfile, spec_dict=spec_dict)
	dco_bbox.scale(scale)
	dco_bbox_lef = BBoxLEFBuilder(dco_bbox, indent_char_width=2)
	dco_bbox_gds = GDSDesign(dco_bbox, layermap_file=asap7_layermapfile)
	dco_bbox_gds.add_polygons()
	dco_bbox_lef.write_lef(projects_dir / f'phyrilog/views2/lef/gen_example_dco_x{scale}.lef')
	dco_bbox_gds.write_gdsfile(projects_dir / f'phyrilog/views2/gds/gen_example_dco_x{scale}.gds')



if __name__ == '__main__':
	spec_dict = {'pin_margin': True,
				 'aspect_ratio': [4,1],
				 'site': 'coreSite',
				 'xwidth': 30,
				 'ywidth': 30,
				 'pins': {
					 'h_layer': 'M4',
					 'v_layer': 'M5',
					 'pin_length': 0.3
				 },
				 'pg_pins':{
					 'h_layer': 'M8',
					 'v_layer': 'M9',
					 'pwr_pin':{
						 'xwidth': 0.215,
						 'ywidth': 1,
						 'layer': 'M5',
						 'side': 'top',
						 'center': 0.48+0.324
					 },
					 'gnd_pin':{
						 'xwidth': 0.215,
						 'ywidth': 1,
						 'layer': 'M5',
						 'side': 'top',
						 'center': 0.48
					 },
				 },
				 'exclude_layers': ['Pad']}
	# test_v1lef(spec_dict)
	# test_v1gds(spec_dict)
	gen_dco_files(spec_dict)
	gen_scaled_dco_files(spec_dict, 4)
	# bbox = test_v2lef(spec_dict)
	# bbox_lef = BBoxLEFBuilder(filename='test_lef.lef', indent_char_width = 2)
	# bbox_lef.make_lef_dict(bbox)
	# print(bbox.pins['sum[0]'].phys_map)
	# pprint.pprint(bbox_lef.blocks)
	# pprint.pprint(bbox_lef.blocks[test2_mod.name].blocks[''].type)
	# bbox_lef.build_lef()
	# print(bbox_lef.lef)
	# bbox_lef.write_lef()
