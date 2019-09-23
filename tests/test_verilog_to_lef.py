from verilog_pin_extract import VerilogModule
from verilog2lef import *
import pprint
import pathlib # I hate you Microsoft

# test_mod = VerilogModule('Memory141', filename='Memory141.v', constfile='const.vh')
test2_mod = VerilogModule('TestParamsAndPorts', filename='test_module.v')
projects_dir = pathlib.Path(__file__).parents[2]
test_techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
test_techfile = str(test_techfile)
# test_techfile = "../hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json"

def test_v2lef():
	bbox = BBoxLEF(test2_mod, test_techfile)
	pprint.pprint(test2_mod.pins)
	pprint.pprint(bbox.pins)
	pprint.pprint(bbox.n_inputs)
	pprint.pprint(bbox.n_outputs)

if __name__=='__main__':
	test_v2lef()