class LEFBuilder:
	"""API for ease of building a LEF file."""
	def __init__(self):
		self.lines = ""
		self.blocks = {}

	def add_lef_header(self, version, bus_bit_chars="[]", divider_char="/"):
		self.lines.append(f"VERSION {version}")
		bus_bit_char_str = "\"" + str(bus_bit_chars) + "\""
		self.lines.append("BUSBITCHARS " + "\"" + str(bus_bit_chars) + "\"")
		self.lines.append("DIVIDERCHAR " + "\"" + str(divider_char) + "\"")

	def add_block(self, type, name):
		"""LEF Blocks are usually grouped under similar indentation"""
		block_dict = {"name_str":name}

