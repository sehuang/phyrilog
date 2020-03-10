from verilog_pin_extract import VerilogModule
import textwrap

class DummyModule(VerilogModule):
	def __init__(self, top, outfile, pin_list):
		self.outfile = outfile
		self.top = top
		self.line_out = ""
		super.__init()__(top, VDD='VDD', VSS='VSS', filename=outfile, constfile=None, clocks=[('clock')], seq_pins=[()])

	def write_file(self):
