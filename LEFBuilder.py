from verilog2phy import PHYDesign, Rectangle, Label

class LEFBlock:
	def __init__(self, type, name, lines):
		self.type = type
		self.name = name
		self.lines = lines
		self.blocks = {}
		self.type_list = set()
		self.layers = {}

	def add_block(self, block_type, name, lines):
		"""LEF Blocks are usually grouped under similar indentation"""
		new_block = LEFBlock(block_type, name, lines)
		self.blocks[name] = new_block
		self.type_list.add(block_type)
		return new_block

	def add_layer(self, layer_name, coords):
		if not self.layers.get(layer_name, None):
			new_layer = LEFLayer(layer_name)
			self.layers[layer_name] = new_layer
			layer = new_layer
		else:
			layer = self.layers[layer_name]
		layer.add_rect([str(x) for x in coords])
		return layer

	def add_pin(self, name, pin_obj):
		new_pin = LEFPin(name, pin_obj)
		self.blocks[name] = new_pin
		new_pin.add_port(pin_obj.phys_objs)

	def add_bbox_obs(self, bbox_phys_obj):
		new_obs = self.add_block('OBS', '', [])
		for rectangle in bbox_phys_obj:
			new_obs.add_layer(rectangle.layer, rectangle.coords)

	def add_pgpin(self, pg, pin_obj):
		new_pgpin = LEFPGPin(pin_obj.name, pin_obj, pg)
		self.blocks[pin_obj.name] = new_pgpin
		new_pgpin.add_port(pin_obj.phys_objs)



	# def add_pin(self, pin_name, pin_obj):
	#     lines = []
	#     lines.append(f"DIRECTION {pin_obj.direction.upper()}")
	#     lines.append(f"USE SIGNAL")
	#     self.add_block('PIN', pin_name, lines)

class LEFPin(LEFBlock):
	def __init__(self, pin_name, pin_obj):
		super().__init__('PIN', pin_obj.name, [])
		self.lines.append(f"DIRECTION {pin_obj.direction.upper()}")
		self.lines.append(f"USE SIGNAL")

	def add_port(self, pin_phys_obj):
		new_port = self.add_block('PORT', '', [])
		for rectangle in pin_phys_obj:
			if isinstance(rectangle, Rectangle):
				new_port.add_layer(rectangle.layer, rectangle.coords)

class LEFPGPin(LEFPin):
	def __init__(self, pin_name, pin_obj, pg):
		super().__init__(pin_obj.name, pin_obj)
		self.lines = []
		self.lines.append(f"DIRECTION {pin_obj.direction.upper()}")
		if pg == 'pwr':
			pg = 'POWER'
		elif pg == 'gnd':
			pg = 'GROUND'
		self.lines.append(f"USE {pg.upper()}")

class LEFLayer(LEFBlock):
	def __init__(self, layer):
		super().__init__('LAYER', layer, [])
		self.rects = []

	def add_rect(self, coords):
		coord_str = " ".join(coords)
		self.rects.append("RECT " + coord_str + " ;")

class LEFBuilder(LEFBlock):
	"""API for ease of building a LEF file."""

	def __init__(self, indent_char_width=2):
		super().__init__('top', 'top', [])
		self.blocks = {}
		self.lines = []
		self.lef = ""
		self.indent_step = indent_char_width

	def add_lef_header(self, version=None, bus_bit_chars="[]", divider_char="/"):
		lines = []
		lines.append(f"VERSION {version}")
		lines.append("BUSBITCHARS " + "\"" + str(bus_bit_chars) + "\"")
		lines.append("DIVIDERCHAR " + "\"" + str(divider_char) + "\"")
		return lines

	# def add_pin(self, parent, name, lines):

	# def add_macro(self, name, lines):
	#     parent = self.blocks

	def build_layer(self, layer, level):
		line_list = []
		layer_header = " ".join([layer.type, layer.name, ';'])
		line_list.append(layer_header.rjust(len(layer_header) + (level * self.indent_step)))
		for rect_str in layer.rects:
			rect_str = rect_str.rjust(len(rect_str) + (level + 1) * self.indent_step)
			line_list.append(rect_str)
		out_str = '\n'.join(line_list)
		return out_str

	def build_block(self, block, level):
		line_list = []
		block_header = " ".join([block.type, block.name])
		line_list.append(block_header.rjust(len(block_header) + (level * self.indent_step)))
		for line in block.lines:
			line_list.append(line.rjust(len(line) + ((level + 1) * self.indent_step)) + " ;")
		if block.blocks:
			for block_obj in block.blocks.values():
				block_str = self.build_block(block_obj, level + 1)
				line_list.append(block_str)
		if block.layers:
			for layer in block.layers.values():
				layer_str = self.build_layer(layer, level + 1)
				line_list.append(layer_str)
		end_str = f'END {block.name}'
		line_list.append(end_str.rjust(len(end_str) + level * self.indent_step))
		out_str = '\n'.join(line_list)


		# for block_type in block.keys():
		#     for block_dict in block[block_type]:
		#         block_header = '\t' * (level + 1) + block_type + " " + block_dict['name'] + '\n'
		#         str_out += block_header
		#         for line in block_dict['lines']:
		#             str_out += '\t' * (level + 1) + line + " ;\n"
		#         if block.get('blocks', None):
		#             for block in block['blocks']:
		#                 str_out += self.build_block(block, level + 1)
		return out_str

	def build_lef(self):
		line_list = []
		for line in self.lines:
			if line == '\n':
				self.lef += line
			else:
				self.lef += line + " ;\n"
		for block in self.blocks.values():
			block_str = self.build_block(block, 0)
			self.lef += block_str

		self.lef += '\n\n'
		self.lef += 'END LIBRARY'

	def write_lef(self, filename):
		if not self.lef:
			self.build_lef()
		with open(filename, 'w') as lef_file:
			lef_file.write(self.lef)



# def add_pin


class BBoxLEFBuilder(LEFBuilder):

	def __init__(self, phy_design, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.make_lef_dict(phy_design)

	def make_lef_dict(self, phy_design: PHYDesign, add_pg_pins=True):
		pins = phy_design.pins
		bbox = phy_design.bboxes
		pg_pins = phy_design.pg_pins
		name = phy_design.name
		class_line = "CLASS CORE"
		header_lines = self.add_lef_header(version=5.6)
		origin_line = f"ORIGIN {phy_design.specs['origin'][0]} {phy_design.specs['origin'][1]}"
		size_line = f"SIZE {phy_design.x_width} BY {phy_design.y_width}"
		sym_line = f"SYMMETRY {phy_design.specs['symmetry']}"
		site_line = f"SITE {phy_design.specs['site']}"

		self.lines += header_lines
		self.lines += '\n'

		# Macro lines
		macro_lines = [class_line, origin_line, size_line, sym_line, site_line]

		macro_block = self.add_block('MACRO', phy_design.name, lines=macro_lines)
		if add_pg_pins:
			for pg, pin in pg_pins.items():
				macro_block.add_pgpin(pg, pin)
		for pin_name, pin in pins.items():
			macro_block.add_pin(pin_name, pin)
		for bbox in bbox.values():
			macro_block.add_bbox_obs(bbox.phys_objs)
