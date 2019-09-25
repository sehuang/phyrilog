import json


class PHYObject:
	def __init__(self, name):
		self.name = name
		self.phys_map = {}

	def add_rect(self, layer, left_x, bot_y, right_x, top_y):
		if layer in self.phys_map.keys():
			self.phys_map[layer].append = [left_x, bot_y, right_x, top_y]
		else:
			self.phys_map[layer] = [[left_x, bot_y, right_x, top_y]]

	# self.phys_map[layer]['shape'] = 'RECT'

	def write_lef_block(self):
		pass


class PHYPortPin(PHYObject):
	def __init__(self, pin_dict, layer, side, x_width, y_width, bus_idx=None):
		super().__init__(None)

		self.pin_dict = pin_dict
		self.name = pin_dict['name']
		self.direction = pin_dict['direction']
		self.type = 'SIGNAL'
		self.layer = layer
		self.side = side
		self.x_width = x_width
		self.y_width = y_width
		# self.is_bus = pin_dict.get("is_bus", False)
		if bus_idx:
			self.bus_idx = bus_idx
		self.block_structure = {}

	def add_rect(self, layer, left_x, bot_y):
		if layer in self.phys_map.keys():
			self.phys_map[layer]['coord'].append = [left_x, bot_y, left_x + self.x_width, bot_y + self.y_width]
		else:
			self.phys_map[layer] = [[left_x, bot_y, left_x + self.x_width, bot_y + self.y_width]]

	def write_lef_block_struct(self, bus_idx=None):
		direction_str = f"DIRECTION {self.direction} ;"
		type_str = f"USE SIGNAL ;"
		if not self.is_bus:
			pin_def_str = f"PIN {self.name}"
		else:
			pin_def_str = f"PIN {self.name}[{bus_idx}]"


class PHYBBox(PHYObject):
	def __init__(self, layers, left_x, bot_y, x_width, y_width):
		super().__init__("BBOX")
		self.type = 'OBS'
		for layer in layers:
			self.add_rect(layer, left_x, bot_y, left_x + x_width, bot_y + y_width)

	def add_rect(self, layer, left_x, bot_y, right_x, top_y):
		if layer in self.phys_map.keys():
			self.phys_map[layer].append = [left_x, bot_y, right_x, top_y]
		else:
			self.phys_map[layer] = [[left_x, bot_y, right_x, top_y]]


# self.phys_map[layer]['shape'] = 'RECT'


class PHYDesign:
	"""Python representation of a PHY Design. Right now this just consumes VerilogModules"""

	def __init__(self, verilog_module, techfile, spec_dict=None):
		self.verilog_pin_dict = verilog_module.pins
		self.name = verilog_module.name

		filetype = techfile.split('.')[-1].lower()  # This normally expects a HAMMER tech.json
		if filetype == 'json':
			self._extract_tech_json_info(techfile)
		elif filetype == 'yaml' or filetype == 'yml':
			raise NotImplementedError
		else:
			raise ValueError(f"Unrecognized File Type .{filetype}")

		self.spec_dict = spec_dict
		self.pins = {}
		self.defaults = {'origin': [0,0],
						 'input_side': 'left',
						 'output_side': 'right',
						 'aspect_ratio': [1, 1],
						 'pin_margin': False,
						 'symmetry': 'X Y',
						 'site': 'core',
						 'pins': {'h_layer': "M2",
								  'v_layer': "M3"
								  }
						 }
		self.specs = self.defaults
		if spec_dict:
			self.specs.update(spec_dict)
		self.x_width = self.specs.get('xwidth', None)
		self.y_width = self.specs.get('ywidth', None)


	def _extract_tech_json_info(self, techfile):
		with open(techfile) as file:
			self.tech_dict = json.load(file)
		stackups = self.tech_dict['stackups'][0]['metals']
		self.metals = {}
		for layer in stackups:
			self.metals[layer['name']] = layer

	def add_pin_objects(self):
		self.n_inputs = 0
		self.n_outputs = 0
		for pin_name, pin_info in self.verilog_pin_dict.items():
			pin_spec = self.specs['pins'].get(pin_name, None)
			direction = pin_info['direction']
			# Pin side definitions
			if pin_spec:
				side = pin_spec.get('side', None)
			else:
				side = None
			if not side:
				side = self.specs.get(f'{direction}_side', None)
			if not side:
				side = self.specs['input_side'] if direction == 'input' else self.specs['output_side']

			# Pin Layer definitions
			if side == 'left' or side == 'right':
				layer = self.specs['pins']['h_layer']
				if pin_spec:
					x_width = pin_spec.get('x_width', 1)
					y_width = pin_spec.get('y_width', self.metals[layer]['min_width'])
				else:
					x_width = 1
					y_width = self.metals[layer]['min_width']
			else:
				layer = self.specs['pins']['v_layer']
				if pin_spec:
					x_width = pin_spec.get('x_width', 1)
					y_width = pin_spec.get('y_width', self.metals[layer]['min_width'])
				else:
					x_width = 'x_width', 1
					y_width = 'y_width', self.metals[layer]['min_width']

			# if self.spec_dict:
			# 	pin_spec = self.specs['pin'].get(pin_name, None)
			# 	# Pin side definitions
			# 	side = pin_spec.get('side', None)
			# 	if not side:
			# 		side = self.spec_dict.get(f'{direction}_side')
			# 	else:
			# 		side = self.defaults['input_side'] if direction == 'input' else self.defaults['output_side']
			#
			# 	# Pin Layer definitions
			# 	if side == 'left' or side == 'right':
			# 		layer = self.spec_dict['pins']['h_layer']
			# 		if pin_spec:
			# 			x_width = pin_spec.get('x_width', 1)
			# 			y_width = pin_spec.get('y_width', self.metals['h_layer']['min_width'])
			# 	else:
			# 		layer = self.spec_dict['pins']['v_layer']
			# 		if pin_spec:
			# 			x_width = pin_spec.get('x_width', 1)
			# 			y_width = pin_spec.get('y_width', self.metals['h_layer']['min_width'])
			# else:
			# 	side = self.defaults['input_side'] if direction == 'input' else self.defaults['output_side']
			# 	if side == 'left' or side == 'right':
			# 		layer = self.defaults['pins']['h_layer']
			# 		x_width = 1
			# 		y_width = self.metals['h_layer']['min_width']
			# 	else:
			# 		layer = self.defaults['pins']['v_layer']
			# 		y_width = 1
			# 		x_width = self.metals['v_layer']['min_width']
			if pin_info.get('is_bus', None):
				self.n_inputs += (direction == 'input') * (pin_info['bus_max'] + 1)
				self.n_outputs += (direction == 'output') * (pin_info['bus_max'] + 1)
				for pin in range(pin_info['bus_max'] + 1):
					self.pins[pin_name + '_' + str(pin)] = PHYPortPin(pin_info, layer, side, round(x_width,3), round(y_width,3),
																	  bus_idx=pin)
			else:
				self.n_inputs += direction == 'input'
				self.n_outputs += direction == 'output'
				self.pins[pin_name] = PHYPortPin(pin_info, layer, side, round(x_width,3), round(y_width,3))

	def define_design_boundaries(self):
		pass


class BBoxPHY(PHYDesign):
	"""Black-boxed LEF object. This class describes LEF stuff"""

	# def __init__(self, verilog_module, techfile: str, xwidth=None, ywidth=None,
	# 			 aspect_ratio=[1, 1], spec_dict=None):
	def __init__(self, verilog_module, techfile, spec_dict=None):
		super().__init__(verilog_module, techfile, spec_dict)

		self.add_pin_objects()

	def define_design_boundaries(self):
		if self.x_width:
			x_width = self.x_width
		elif self.y_width:
			x_width = self.y_width * self.aspect_ratio[1] / self.aspect_ratio[0]
		else:
			x_width = None  # Wait until later to figure this out

		if self.y_width:
			y_width = self.y_width
		elif self.x_width:
			y_width = self.x_width * self.aspect_ratio[0] / self.aspect_ratio[1]
		else:
			y_width = None  # Wait until later to figure this out

		self.pin_sides_dict = {'left': [],
						  'right': [],
						  'top': [],
						  'bottom': []}
		for pin in self.pins.values():
			self.pin_sides_dict[pin.side].append(pin)
		min_y_pins = max(len(self.pin_sides_dict['left']), len(self.pin_sides_dict['right']))
		min_x_pins = max(len(self.pin_sides_dict['top']), len(self.pin_sides_dict['bottom']))
		# if self.spec_dict:
		# 	h_pin_width = self.metals[self.spec_dict['pins']['h_layer']]['min_width']
		# 	v_pin_width = self.metals[self.spec_dict['pins']['v_layer']]['min_width']
		# 	h_pin_pitch = self.metals[self.spec_dict['pins']['h_layer']]['pitch']
		# 	v_pin_pitch = self.metals[self.spec_dict['pins']['v_layer']]['pitch']
		# else:
		# 	h_pin_width = self.metals[self.defaults['pins']['h_layer']]['min_width']
		# 	v_pin_width = self.metals[self.defaults['pins']['v_layer']]['min_width']
		# 	h_pin_pitch = self.metals[self.defaults['pins']['h_layer']]['pitch']
		# 	v_pin_pitch = self.metals[self.defaults['pins']['v_layer']]['pitch']
		h_pin_width = self.metals[self.specs['pins']['h_layer']]['min_width']
		v_pin_width = self.metals[self.specs['pins']['v_layer']]['min_width']
		h_pin_pitch = self.metals[self.specs['pins']['h_layer']]['pitch']
		v_pin_pitch = self.metals[self.specs['pins']['v_layer']]['pitch']
		min_y_dim = (min_y_pins * h_pin_width) + ((min_y_pins - 1) * h_pin_pitch) if min_y_pins > 0 else (
				min_y_pins * h_pin_width)
		min_x_dim = (min_x_pins * v_pin_width) + ((min_x_pins - 1) * v_pin_pitch) if min_x_pins > 0 else (
				min_x_pins * v_pin_width)

		if not x_width:
			x_width = min_x_dim
		if not y_width:
			y_width = min_y_dim
		if x_width == 0 and y_width > 0:
			x_width = y_width * self.specs['aspect_ratio'][1]
		if y_width == 0 and x_width > 0:
			y_width = x_width * self.specs['aspect_ratio'][0]
		if self.specs['pin_margin']:
			x_width = x_width + v_pin_pitch
			y_width = y_width + h_pin_pitch
		self.bbox_x_width = round(x_width, 3)
		self.bbox_y_width = round(y_width, 3)
		self.bbox_left_margin = round(max([pin.x_width for pin in  self.pin_sides_dict['left']], default=0), 3)
		self.bbox_right_margin = round(max([pin.x_width for pin in self.pin_sides_dict['right']], default=0), 3)
		self.bbox_top_margin = round(max([pin.y_width for pin in self.pin_sides_dict['top']], default=0), 3)
		self.bbox_bot_margin = round(max([pin.y_width for pin in self.pin_sides_dict['bottom']], default=0), 3)
		self.x_width = round(self.bbox_x_width + self.bbox_left_margin + self.bbox_right_margin, 3)
		self.y_width = round(self.bbox_y_width + self.bbox_top_margin + self.bbox_bot_margin, 3)

	def build_design_repr(self):
		origin = [0, 0]
		h_pin_width = self.metals[self.specs['pins']['h_layer']]['min_width']
		v_pin_width = self.metals[self.specs['pins']['v_layer']]['min_width']
		h_pin_pitch = self.metals[self.specs['pins']['h_layer']]['pitch']
		v_pin_pitch = self.metals[self.specs['pins']['v_layer']]['pitch']
		bbox_bot_left_corner = [self.bbox_left_margin, self.bbox_bot_margin]
		bbox_top_right_corner = [self.x_width - self.bbox_right_margin, self.y_width - self.bbox_top_margin]
		if self.specs['pin_margin']:
			x_corr = v_pin_pitch / 2
			y_corr = h_pin_pitch / 2
		else:
			x_corr = 0
			y_corr = 0
		left_pin_lower_corner = [bbox_bot_left_corner[0], round(round((self.bbox_bot_margin + y_corr) / h_pin_width) * h_pin_pitch, 3)]
		right_pin_lower_corner = [bbox_top_right_corner[0], round(round((self.bbox_bot_margin + y_corr) / h_pin_width) * h_pin_pitch, 3)]
		bot_pin_lower_corner =[round(round((bbox_bot_left_corner[0] + x_corr) / v_pin_width), 3), 0]
		top_pin_lower_corner =[round(round((bbox_top_right_corner[0] + x_corr) / v_pin_width), 3), self.y_width]

		self.bboxes = {
			'BBOX': PHYBBox(self.metals.keys(), bbox_bot_left_corner[0], bbox_bot_left_corner[1], self.bbox_x_width,
							self.bbox_y_width)}
		for pin in self.pin_sides_dict['left']:
			pin.add_rect(self.specs['pins']['h_layer'], left_pin_lower_corner[0], left_pin_lower_corner[1])
			left_pin_lower_corner[1] = round(left_pin_lower_corner[1] + h_pin_width + h_pin_pitch, 3)

		for pin in self.pin_sides_dict['right']:
			pin.add_rect(self.specs['pins']['h_layer'], right_pin_lower_corner[0], right_pin_lower_corner[1])
			right_pin_lower_corner[1] = round(right_pin_lower_corner[1] + h_pin_width + h_pin_pitch, 3)

		for pin in self.pin_sides_dict['bottom']:
			pin.add_rect(self.specs['pins']['v_layer'], bot_pin_lower_corner[0], bot_pin_lower_corner[1])
			bot_pin_lower_corner[0] = round(bot_pin_lower_corner[0] + v_pin_width + v_pin_pitch, 3)

		for pin in self.pin_sides_dict['top']:
			pin.add_rect(self.specs['pins']['v_layer'], top_pin_lower_corner[0], top_pin_lower_corner[1])
			top_pin_lower_corner[0] = round(top_pin_lower_corner[0] + v_pin_width + v_pin_pitch, 3)
