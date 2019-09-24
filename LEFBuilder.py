from verilog2lef import PHYDesign

class LEFBuilder:
	"""API for ease of building a LEF file."""
	def __init__(self):
		self.lines = []
		self.blocks = {}

	def add_lef_header(self, version=None, bus_bit_chars="[]", divider_char="/"):
		lines = []
		lines.append(f"VERSION {version}")
		lines.append("BUSBITCHARS " + "\"" + str(bus_bit_chars) + "\"")
		lines.append("DIVIDERCHAR " + "\"" + str(divider_char) + "\"")
		return lines

	def add_block(self, parent, type, name, lines):
		"""LEF Blocks are usually grouped under similar indentation"""
		parent['blocks'] = {}
		parent['blocks'][type] = {'name': name,
								  'lines': lines}

	# def add_pin

class BBoxLEFBuilder(LEFBuilder):

	def __init__(self):
		super().__init__()

	def make_lef(self, thing: PHYDesign):
		pins = thing.pins
		bbox = thing.bbox
		name = thing.name
		header_lines = self.add_lef_header(version=5.6)

