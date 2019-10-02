import json
import numpy as np

class Rectangle:
	"""Represents a physical rectangle"""
	def __init__(self, layer, left_x, bot_y, right_x, top_y, purpose=['drawing']):
		self.layer = layer
		self.coords = [round(left_x, 3), round(bot_y, 3), round(right_x, 3), round(top_y, 3)]
		self.purpose = purpose

	def scale(self, scale_factor):
		coord_arr = np.asarray(self.coords) * scale_factor
		self.coords = coord_arr.tolist()

class Label:
	def __init__(self, text, layer, position, show=True):
		self.text = text
		self.purpose = ['label']
		self.layer = layer
		self.coords = [round(position[0], 3), round(position[1], 3)]
		self.show = show

	def scale(self, scale_factor):
		coord_arr = np.asarray(self.coords) * scale_factor
		self.coords = coord_arr.tolist()

class PHYObject:
	def __init__(self, name):
		self.name = name
		self.purpose = None
		self.phys_objs = []

	def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0, purpose=['drawing']):
		self.phys_objs.append(Rectangle(layer, left_x, bot_y, right_x, top_y, purpose))

	# self.phys_map[layer]['shape'] = 'RECT'

	def write_lef_block(self):
		pass


class PHYPortPin(PHYObject):
	def __init__(self, pin_dict, layer, side, x_width, y_width, center=None, bus_idx=None):
		super().__init__(None)

		self.pin_dict = pin_dict
		self.name = pin_dict['name']
		self.direction = pin_dict['direction']
		self.layer = layer
		self.side = side
		self.x_width = x_width
		self.y_width = y_width
		self.center = center
		# self.is_bus = pin_dict.get("is_bus", False)
		if isinstance(bus_idx, int):
			self.bus_idx = bus_idx
			self.name = self.name + f'[{self.bus_idx}]'
		self.block_structure = {}

	def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0, purpose=['drawing', 'pin']):
		right_x = left_x + self.x_width
		top_y = bot_y + self.y_width
		self.phys_objs.append(Rectangle(layer, left_x, bot_y, right_x, top_y, purpose))
		self.add_label(layer, ((right_x + left_x) / 2, (top_y + bot_y) / 2))

	def add_label(self, layer, position):
		self.phys_objs.append(Label(self.name, layer, position, show=True))

	def scale(self, scale_factor):
		for rect in self.phys_objs:
			rect.scale(scale_factor)

class PHYBBox(PHYObject):
	def __init__(self, layers, left_x, bot_y, x_width, y_width):
		super().__init__("BBOX")
		self.purpose = 'blockage'
		for layer in layers:
			self.add_rect(layer, left_x, bot_y, left_x + x_width, bot_y + y_width)

	def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0, purpose=['blockage']):
		self.phys_objs.append(Rectangle(layer, left_x, bot_y, right_x, top_y, purpose))

	def scale(self, scale_factor):
		for rect in self.phys_objs:
			rect.scale(scale_factor)

class PHYDesign:
	"""Python representation of a PHY Design. Right now this just consumes VerilogModules"""

	def __init__(self, verilog_module, techfile, spec_dict=None):
		self.verilog_pin_dict = verilog_module.pins
		self.verilog_pg_pin_dict = verilog_module.power_pins
		self.name = verilog_module.name

		techfile = str(techfile) if not isinstance(techfile, str) else techfile
		filetype = techfile.split('.')[-1].lower()  # This normally expects a HAMMER tech.json
		if filetype == 'json':
			self._extract_tech_json_info(techfile)
		elif filetype == 'yaml' or filetype == 'yml':
			raise NotImplementedError
		else:
			raise ValueError(f"Unrecognized File Type .{filetype}")

		self.spec_dict = spec_dict
		self.pins = {}
		self.pg_pins = {}
		self.phys_objs = []
		self.defaults = {'origin': [0, 0],
						 'units': 1e-6,
						 'precision': 1e-9,
						 'input_side': 'left',
						 'output_side': 'right',
						 'pin_margin': False,
						 'symmetry': 'X Y',
						 'site': 'core',
						 'pins': {'h_layer': "M2",
								  'v_layer': "M3"
								  },
						 'pg_pins': {'h_layer': "M2",
									 'v_layer': "M3",
									 'pwr_pin': {'layer': 'M3',
												 'center': None,
												 'side': 'top'},
									 'gnd_pin': {'layer': 'M3',
												 'center': None,
												 'side': 'top'}}
						 }
		self.specs = self.defaults
		if spec_dict:
			self.specs.update(spec_dict)
		self.x_width = self.specs.get('xwidth', None)
		self.y_width = self.specs.get('ywidth', None)
		# self.aspect_ratio = self.specs_dict.get('aspect_ratio', None)
		self.polygons = {'pins': self.pins,
						 'pg_pins': self.pg_pins}

	def _extract_tech_json_info(self, techfile):
		with open(techfile) as file:
			self.tech_dict = json.load(file)
		stackups = self.tech_dict['stackups'][0]['metals']
		self.metals = {}
		for layer in stackups:
			self.metals[layer['name']] = layer

	def add_pg_pin_objects(self):
		power_pin_name = self.verilog_pg_pin_dict['power_pin']
		ground_pin_name = self.verilog_pg_pin_dict['ground_pin']
		pg_pin_specs = self.specs['pg_pins']
		pwr_pin_specs = self.specs['pg_pins']['pwr_pin']
		gnd_pin_specs = self.specs['pg_pins']['gnd_pin']



		if pwr_pin_specs['side'] == 'top' or pwr_pin_specs['side'] == 'bottom':
			if not pwr_pin_specs.get('xwidth', None):
				pwr_pin_specs['xwidth'] = self.metals[pwr_pin_specs['layer']]['min_width']
			if not pwr_pin_specs.get('ywidth', None):
				pwr_pin_specs['ywidth'] = 1
		else:
			if not pwr_pin_specs.get('ywidth', None):
				pwr_pin_specs['ywidth'] = self.metals[pwr_pin_specs['layer']]['min_width']
			if not pwr_pin_specs.get('xwidth', None):
				pwr_pin_specs['xwidth'] = 1

		if gnd_pin_specs['side'] == 'top' or gnd_pin_specs['side'] == 'bottom':
			if not gnd_pin_specs.get('xwidth', None):
				gnd_pin_specs['xwidth'] = self.metals[gnd_pin_specs['layer']]['min_width']
			if not gnd_pin_specs.get('ywidth', None):
				gnd_pin_specs['ywidth'] = 1
		else:
			if not gnd_pin_specs.get('ywidth', None):
				gnd_pin_specs['ywidth'] = self.metals[gnd_pin_specs['layer']]['min_width']
			if not gnd_pin_specs.get('xwidth', None):
				gnd_pin_specs['xwidth'] = 1

		pwr_pin_dict = {'name': power_pin_name,
						'direction': 'inout',
						'is_analog': False}
		gnd_pin_dict = {'name': ground_pin_name,
						'direction': 'inout',
						'is_analog': False}
		pwr_pin = PHYPortPin(pwr_pin_dict, pwr_pin_specs['layer'],
							 pwr_pin_specs['side'],
							 round(pwr_pin_specs['xwidth'], 3),
							 round(pwr_pin_specs['ywidth'], 3),
							 center=pg_pin_specs['pwr_pin'].get('center', None))
		gnd_pin = PHYPortPin(gnd_pin_dict, pg_pin_specs['gnd_pin']['layer'],
							 pg_pin_specs['gnd_pin']['side'],
							 round(pg_pin_specs['gnd_pin']['xwidth'], 3),
							 round(pg_pin_specs['gnd_pin']['ywidth'], 3),
							 center=pg_pin_specs['gnd_pin'].get('center', None))
		pwr_pin.type = 'POWER'
		gnd_pin.type = 'GROUND'
		self.pg_pins['pwr'] = pwr_pin
		self.pg_pins['gnd'] = gnd_pin
		self.phys_objs.append(pwr_pin)
		self.phys_objs.append(gnd_pin)

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
			if pin_info.get('is_bus', None):
				self.n_inputs += (direction == 'input') * (pin_info['bus_max'] + 1)
				self.n_outputs += (direction == 'output') * (pin_info['bus_max'] + 1)
				for pin in range(pin_info['bus_max'] + 1):
					self.pins[pin_name + '[' + str(pin) + ']'] = PHYPortPin(pin_info, layer, side, round(x_width, 3),
																			round(y_width, 3),
																			bus_idx=pin)
			else:
				self.n_inputs += direction == 'input'
				self.n_outputs += direction == 'output'
				self.pins[pin_name] = PHYPortPin(pin_info, layer, side, round(x_width, 3), round(y_width, 3))
		self.phys_objs += list(self.pins.values())

	def define_design_boundaries(self):
		pass

	def scale(self, scale_factor = 1):
		for obj in self.phys_objs:
			obj.scale(scale_factor)
		self.x_width = round(self.x_width * scale_factor, 3)
		self.y_width = round(self.y_width * scale_factor, 3)


class BBoxPHY(PHYDesign):
	"""Black-boxed LEF object. This class describes LEF stuff"""

	# def __init__(self, verilog_module, techfile: str, xwidth=None, ywidth=None,
	# 			 aspect_ratio=[1, 1], spec_dict=None):
	def __init__(self, verilog_module, techfile, spec_dict=None):
		super().__init__(verilog_module, techfile, spec_dict)

		self.add_pin_objects()
		self.add_pg_pin_objects()
		self.define_design_boundaries()
		self.build_design_repr()

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
		for pg_pin in self.pg_pins.values():
			self.pin_sides_dict[pg_pin.side].append(pg_pin)
		min_h_pins = max(len(self.pin_sides_dict['left']), len(self.pin_sides_dict['right']))
		min_v_pins = max(len(self.pin_sides_dict['top']), len(self.pin_sides_dict['bottom']))

		h_pin_width = self.metals[self.specs['pins']['h_layer']]['min_width']
		v_pin_width = self.metals[self.specs['pins']['v_layer']]['min_width']
		h_pin_pitch = self.metals[self.specs['pins']['h_layer']]['pitch']
		v_pin_pitch = self.metals[self.specs['pins']['v_layer']]['pitch']
		# min_y_dim = (min_h_pins * h_pin_width) + ((min_h_pins - 1) * h_pin_pitch) if min_h_pins > 0 else (
		# 		min_h_pins * h_pin_width)
		min_y_dim = max(sum([pin.y_width for pin in self.pin_sides_dict['left']]),
						sum([pin.y_width for pin in self.pin_sides_dict['right']])) + ((min_h_pins - 1) * h_pin_pitch)
		# min_x_dim = (min_v_pins * v_pin_width) + ((min_v_pins - 1) * v_pin_pitch) if min_v_pins > 0 else (
		# 		min_v_pins * v_pin_width)
		min_x_dim = max(sum([pin.x_width for pin in self.pin_sides_dict['top']]),
						sum([pin.x_width for pin in self.pin_sides_dict['bottom']])) + ((min_v_pins - 1) * v_pin_pitch)

		# max_hpin_size = 0
		# max_vpin_size = 0
		# for x_side in [self.pin_sides_dict['left'], self.pin_sides_dict['right']]:
		# 	for pin in x_side:
		# 		if max_hpin_size < pin.x_width:
		# 			min_y_dim = pin.x_width
		# for y_side in [self.pin_sides_dict['top'], self.pin_sides_dict['bottom']]:
		# 	for pin in y_side:
		# 		if min_x_dim < pin.y_width:
		# 			min_x_dim = pin.y_width

		if not x_width:
			x_width = min_x_dim
		if not y_width:
			y_width = min_y_dim
		if self.specs.get('aspect_ratio', None):
			if not self.specs.get('xwidth', None) or not self.specs.get('ywidth', None):
				if y_width * self.specs['aspect_ratio'][1] > min_x_dim:
					x_width = y_width / self.specs['aspect_ratio'][1] * self.specs['aspect_ratio'][0]
				elif x_width * self.specs['aspect_ratio'][0] > min_y_dim:
					y_width = x_width / self.specs['aspect_ratio'][0] * self.specs['aspect_ratio'][1]
		if x_width == 0 and y_width > 0:
			x_width = y_width * self.specs['aspect_ratio'][1]
		if y_width == 0 and x_width > 0:
			y_width = x_width * self.specs['aspect_ratio'][0]
		if self.specs['pin_margin']:
			x_width = x_width + (2 * v_pin_pitch)
			y_width = y_width + (2 * h_pin_pitch)
		self.bbox_x_width = round(x_width, 3)
		self.bbox_y_width = round(y_width, 3)
		self.bbox_left_margin = round(max([pin.x_width for pin in self.pin_sides_dict['left']], default=0), 3)
		self.bbox_right_margin = round(max([pin.x_width for pin in self.pin_sides_dict['right']], default=0), 3)
		self.bbox_top_margin = round(max([pin.y_width for pin in self.pin_sides_dict['top']], default=0), 3)
		self.bbox_bot_margin = round(max([pin.y_width for pin in self.pin_sides_dict['bottom']], default=0), 3)
		self.x_width = round(self.bbox_x_width + self.bbox_left_margin + self.bbox_right_margin, 3)
		self.y_width = round(self.bbox_y_width + self.bbox_top_margin + self.bbox_bot_margin, 3)

	def place_pins(self, start_corner, side_dict, orientation):
		for pin in side_dict:
			layer = pin.layer
			pin_width = self.metals[layer]['min_width']
			pin_pitch = self.metals[layer]['pitch']
			if pin.center:
				if orientation == 'horizontal':
					start_corner[1] = round(pin.center - pin_width/2, 3)
				else:
					start_corner[0] = round(pin.center - pin_width / 2, 3)
			pin.add_rect(layer, start_corner[0], start_corner[1])
			if orientation == 'horizontal':
				start_corner[1] = round(start_corner[1] + pin_width + pin_pitch, 3)
			else:
				start_corner[0] = round(start_corner[0] + pin_width + pin_pitch, 3)

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

		self.pin_place_start_corners = {}
		self.pin_place_start_corners['left'] = [0,
												round(
													np.ceil((self.bbox_bot_margin + y_corr) / h_pin_width) * h_pin_width,
													3)]
		self.pin_place_start_corners['right'] = [bbox_top_right_corner[0],
												 round(
													 np.ceil((self.bbox_bot_margin + y_corr) / h_pin_width) * h_pin_width,
													 3)]
		self.pin_place_start_corners['bottom'] = \
			[round(np.ceil((self.bbox_left_margin + x_corr) / v_pin_width) * v_pin_width, 3), 0]
		self.pin_place_start_corners['top'] = \
			[round(np.ceil((self.bbox_left_margin + x_corr) / v_pin_width) * v_pin_width, 3),
			 bbox_top_right_corner[1]]

		bbox_layers = []
		for layer in self.metals:
			if layer not in self.specs['exclude_layers']:
				bbox_layers.append(layer)
		self.bboxes = {
			'BBOX': PHYBBox(bbox_layers, bbox_bot_left_corner[0], bbox_bot_left_corner[1], self.bbox_x_width,
							self.bbox_y_width)}
		self.polygons['bboxes'] = self.bboxes
		self.phys_objs += list(self.bboxes.values())

		for side in self.pin_sides_dict.keys():
			orientation = 'horizontal' if side in ['left', 'right'] else 'vertical'
			self.place_pins(self.pin_place_start_corners[side], self.pin_sides_dict[side], orientation)
#
# for pin in self.pin_sides_dict['left']:
# 	pin.add_rect(self.specs['pins']['h_layer'], left_pin_lower_corner[0], left_pin_lower_corner[1])
# 	left_pin_lower_corner[1] = round(left_pin_lower_corner[1] + h_pin_width + h_pin_pitch, 3)
#
# for pin in self.pin_sides_dict['right']:
# 	pin.add_rect(self.specs['pins']['h_layer'], right_pin_lower_corner[0], right_pin_lower_corner[1])
# 	right_pin_lower_corner[1] = round(right_pin_lower_corner[1] + h_pin_width + h_pin_pitch, 3)
#
# for pin in self.pin_sides_dict['bottom']:
# 	pin.add_rect(self.specs['pins']['v_layer'], bot_pin_lower_corner[0], bot_pin_lower_corner[1])
# 	bot_pin_lower_corner[0] = round(bot_pin_lower_corner[0] + v_pin_width + v_pin_pitch, 3)
#
# for pin in self.pin_sides_dict['top']:
# 	pin.add_rect(self.specs['pins']['v_layer'], top_pin_lower_corner[0], top_pin_lower_corner[1])
# 	top_pin_lower_corner[0] = round(top_pin_lower_corner[0] + v_pin_width + v_pin_pitch, 3)
