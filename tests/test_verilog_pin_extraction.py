from verilog_pin_extract import VerilogModule
import pprint


def test_sds(top):
	design = VerilogModule(top, filename="test_module.v")
	pprint.pprint(design.pins)

if __name__=='__main__':
	mod = VerilogModule('Memory141', filename='Memory141.v', constfile='const.vh')
	pprint.pprint(mod.ports_json_dict)