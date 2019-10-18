from verilog_pin_extract import VerilogModule
from verilog2phy import *
from utilities import *
import numpy as np
import enum

pin_placement_algorithm = ['casual', 'strict']
pin_spacing_options = ['min_pitch', 'distributed']
pg_pin_placement_options = ['small_pins', 'straps', 'interlaced']

pin_specs = {'pins': {'h_layer': "M2",
					  'v_layer': "M3",
					  'pin_length': 1
					  },
			 'pg_pins': {'h_layer': "M2",
						 'v_layer': "M3",
						 'power_pin': {'layer': 'M3',
									   'center': None,
									   'side': 'top'},
						 'ground_pin': {'layer': 'M3',
										'center': None,
										'side': 'top'}}
			 }


class PinPlacer:
	"""Pin placement engine"""

	def __init__(self, pins_dict, pg_pins_dict, techfile, pin_specs=dict(), options_dict=dict()):
		self.pins_dict = pins_dict
		self.pg_pins_dict = pg_pins_dict
		self.defaults = {'origin': [0, 0],
						 'units': 1e-6,
						 'precision': 1e-9,
						 'input_side': 'left',
						 'output_side': 'right',
						 'pin_margin': False,
						 'strictness': 'casual',
						 'port_sides': {
							 'input': 'left',
							 'output': 'right',
						 },
						 'pg_pin_sides': {
							 'power_pin': 'top',
							 'ground_pin': 'top'
						 },
						 'spacing': {'common': 'min_pitch'},
						 'pin_spacing': 'min_pitch',
						 'pg_pin_placement': 'small_pins',
						 'design_boundary': (10, 10),
						 'internal_box': [1, 1, 9, 9],
						 'pins': {'h_layer': "M2",
								  'v_layer': "M3",
								  'pin_length': 1}
						 }
		self.specs = r_update(self.defaults, pin_specs)
		self.specs = r_update(self.specs, options_dict)
		self._extract_techfile(techfile)
		self.pins = []
		self._define_pg_pin_dicts()

	def _define_pg_pin_dicts(self):
		pg_pin_dicts = {}
		for purpose, pin in self.pg_pins_dict.items():
			pg_pin_dicts[purpose] = {'name': pin,
									 'direction': 'inout',
									 'is_analog': False}
		self.power_pin = pg_pin_dicts['power_pin']
		self.ground_pin = pg_pin_dicts['ground_pin']

	def _extract_techfile(self, techfile):
		techfile = str(techfile) if not isinstance(techfile, str) else techfile
		if isinstance(techfile, str):
			filetype = techfile.split('.')[-1].lower()  # This normally expects a HAMMER tech.json
		else:
			filetype = techfile.suffix.split('.')[-1].lower()
		if filetype == 'json':
			self._extract_tech_json_info(techfile)
		elif filetype == 'yaml' or filetype == 'yml':
			raise NotImplementedError
		else:
			raise ValueError(f"Unrecognized File Type .{filetype}")

	def _extract_tech_json_info(self, techfile):
		with open(techfile) as file:
			self.tech_dict = json.load(file)
		stackups = self.tech_dict['stackups'][0]['metals']
		self.metals = {}
		for layer in stackups:
			self.metals[layer['name']] = layer
		self.h_pin_width = self.metals[self.specs['pins']['h_layer']]['min_width']
		self.v_pin_width = self.metals[self.specs['pins']['v_layer']]['min_width']
		self.h_pin_pitch = self.metals[self.specs['pins']['h_layer']]['pitch']
		self.v_pin_pitch = self.metals[self.specs['pins']['v_layer']]['pitch']

	# def _make_pin_obj(self, pin_dict,):

	def _sort_pins_by_side(self):
		self.pin_sides_dict = {'left': [],
							   'right': [],
							   'top': [],
							   'bottom': []}
		pin_specs = self.specs['pins']
		for pin in self.pins_dict.values():
			side = self.specs['port_sides'][pin['direction']]
			if pin['name'] in pin_specs.keys():
				side = pin_specs[pin['name']].get('side', side)
			orientation = 'h' if side in ['left', 'right'] else 'v'
			x_width = pin_specs['pin_length'] if orientation == 'h' else self.metals[pin_specs['v_layer']][
				'min_width']
			y_width = pin_specs['pin_length'] if orientation == 'v' else self.metals[pin_specs['h_layer']][
				'min_width']
			layer = self.specs['pins']['h_layer'] if orientation == 'h' else self.specs['pins']['v_layer']
			center = None
			if pin['name'] in self.specs['pins'].keys():
				layer = self.specs['pins'][pin['name']].get('layer', layer)
				center = self.specs['pins'][pin['name']].get('center', None)
			if 'is_bus' in pin.keys():
				for bus_idx in range(pin['bus_max'] + 1):
					pin_obj = PHYPortPin(pin, layer, side, x_width, y_width, bus_idx=bus_idx)
					pin_obj.name = pin['name'] + '[' + str(bus_idx) + ']'
					self.pin_sides_dict[side].append(pin_obj)
					self.pins.append(pin_obj)
			else:
				pin_obj = PHYPortPin(pin, layer, side, x_width, y_width, center=center)
				self.pin_sides_dict[side].append(pin_obj)
				self.pins.append(pin_obj)
		if self.specs['pg_pin_placement'] == pg_pin_placement_options[0]:
			for purpose, pg_pin in self.pg_pins_dict.items():
				pg_pin_dict = {'name': pg_pin,
							   'direction': 'inout',
							   'is_analog': False,
							   'purpose': purpose}
				side = self.specs['pg_pin_sides'][purpose]
				orientation = 'h' if side in ['left', 'right'] else 'v'
				x_width = pin_specs['pin_length'] if orientation == 'h' else self.metals[pin_specs['v_layer']][
					'min_width']
				y_width = pin_specs['pin_length'] if orientation == 'v' else self.metals[pin_specs['h_layer']][
					'min_width']
				layer = self.specs['pg_pins']['h_layer'] if orientation == 'h' else self.specs['pg_pins']['v_layer']
				if purpose in self.specs['pg_pins'].keys():
					layer = self.specs['pg_pins'][purpose].get('layer', layer)
					center = self.specs['pg_pins'][purpose].get('center', None)
				if 'multiplier' in self.specs['pg_pins'].keys():
					for idx in range(pg_pin['multiplier'] + 1):
						spacing = 2 * self.metals[layer]['min_width'] + 2 * self.metals[layer]['pitch']
						new_cent = center + round(idx * spacing, 3)
						pin_obj = PHYPortPin(pin, layer, side, x_width, y_width, center=new_cent)
						self.pin_sides_dict[side].append(pin_obj)
						self.pins.append(pin_obj)
				else:
					pin_obj = PHYPortPin(pin, layer, side, x_width, y_width, center=center)
					self.pin_sides_dict[side].append(pin_obj)
					self.pins.append(pin_obj)

	# def _assign_pin_dimensions(self):
	# 	pin_specs = self.specs['pins']
	# 	metals = self.metals
	# 	for side, pins in self.pin_sides_dict.items():
	# 		orientation = 'h' if side in ['left', 'right'] else 'v'
	# 		for pin in pins:
	# 			if 'x_width' not in pin.keys():
	# 				x_width = pin_specs['pin_length'] if orientation == 'h' else metals[pin_specs['v_layer']][
	# 					'min_width']
	# 			if 'y_width' not in pin.keys():
	# 				y_width = pin_specs['pin_length'] if orientation == 'v' else metals[pin_specs['h_layer']][
	# 					'min_width']
	# 			pin['x_width'] = x_width
	# 			pin['y_width'] = y_width

	def _autodefine_boundaries(self):
		pin_specs = self.specs['pins']
		min_h_pins = round(max(len(self.pin_sides_dict['left']), len(self.pin_sides_dict['right'])), 3)
		min_v_pins = round(max(len(self.pin_sides_dict['top']), len(self.pin_sides_dict['bottom'])), 3)
		min_y_dim = round(max(sum([pin.y_width for pin in self.pin_sides_dict['left']]),
							  sum([pin.y_width for pin in self.pin_sides_dict['right']])) + (
								  (min_h_pins - 1) * self.h_pin_pitch), 3)
		min_x_dim = round(max(sum([pin.x_width for pin in self.pin_sides_dict['top']]),
							  sum([pin.x_width for pin in self.pin_sides_dict['bottom']])) + (
								  (min_v_pins - 1) * self.v_pin_pitch), 3)
		max_b_pin_length = max_none([pin.y_width for pin in self.pin_sides_dict['bottom']])
		max_l_pin_length = max_none([pin.x_width for pin in self.pin_sides_dict['left']])
		max_r_pin_length = max_none([pin.x_width for pin in self.pin_sides_dict['right']])
		max_t_pin_length = max_none([pin.y_width for pin in self.pin_sides_dict['top']])
		self.specs['internal_box'] = [max_l_pin_length, max_b_pin_length, min_x_dim, min_y_dim]
		self.specs['design_boundary'] = [
			min_x_dim + max_l_pin_length + max_r_pin_length, min_y_dim + max_t_pin_length + max_b_pin_length]
		if self.specs['pin_margin']:
			self.specs['design_boundary'] = [
				round(min_x_dim + max_l_pin_length + max_r_pin_length + 2 * self.v_pin_pitch, 3),
				round(min_y_dim + max_t_pin_length + max_b_pin_length + 2 * self.h_pin_pitch, 3)]
		if self.specs.get('aspect_ratio', None):
			dom_dim_idx = self.specs['design_boundary'].index(max(self.specs['design_boundary']))
			sub_dim_idx = self.specs['design_boundary'].index(min(self.specs['design_boundary']))
			sub_dim = round(self.specs['design_boundary'][dom_dim_idx] / self.specs['aspect_ratio'][dom_dim_idx] *
							self.specs['aspect_ratio'][sub_dim_idx], 3)
			self.specs['design_boundary'][sub_dim_idx] = round(sub_dim, 3)
			box_sides = [self.specs['internal_box'][2] - self.specs['internal_box'][0],
						 self.specs['internal_box'][3] - self.specs['internal_box'][1]]
			dom_dim_idx = box_sides.index(max(box_sides))
			sub_dim_idx = box_sides.index(min(box_sides))
			sub_dim = round(box_sides[dom_dim_idx] / self.specs['aspect_ratio'][dom_dim_idx] *
							self.specs['aspect_ratio'][sub_dim_idx], 3)
			box_sides[sub_dim_idx] = sub_dim
			self.specs['internal_box'][2 + sub_dim_idx] = round(self.specs['internal_box'][0 + sub_dim_idx] + sub_dim, 3)
		self.specs['bound_box'] = self.specs['origin'] + list(self.specs['design_boundary'])

	def _place_defined_pins(self):
		self.placed_pin_sides_dict = {'left': [],
									  'right': [],
									  'top': [],
									  'bottom': []}
		pin_specs = self.specs['pins']
		for side_name, side in self.pin_sides_dict.items():
			for pin in side:
				if pin.name in pin_specs.keys():
					x_pos = pin_specs[pin.name].get('x_pos', None)
					y_pos = pin_specs[pin.name].get('y_pos', None)
					center = pin_specs[pin.name].get('center', None)
					if any([x_pos, y_pos, center]):  # I'm going to assume that only center is given for now
						# TODO: Add support for y and x corner definitions
						if side_name in ['left', 'right']:
							layer = pin_specs['h_layer']
							layer = pin_specs[pin.name].get('layer', layer)
							x_width = round(pin_specs[pin.name].get('x_width', pin_specs['pin_length']), 3)
							y_width = round(pin_specs[pin.name].get('y_width', self.h_pin_width), 3)
							left_x = 0 if side_name == 'left' else round(self.specs['design_boundary'][0] - x_width, 3)
							right_x = x_width if side_name == 'left' else round(self.specs['design_boundary'][0], 3)
							top_y = round(center + y_width / 2, 3)
							bot_y = round(center - y_width / 2, 3)
						else:
							layer = pin_specs['v_layer']
							layer = pin_specs[pin.name].get('layer', layer)
							x_width = round(pin_specs[pin.name].get('x_width', pin_specs['pin_length']), 3)
							y_width = round(pin_specs[pin.name].get('y_width', self.h_pin_width), 3)
							left_x = round(center - x_width / 2, 3)
							right_x = round(center + x_width / 2, 3)
							bot_y = 0 if side_name == 'bottom' else round(self.specs['design_boundary'][1] - y_width, 3)
							top_y = y_width if side_name == 'bottom' else round(self.specs['design_boundary'][1], 3)
						pin.add_rect(layer, left_x=left_x, bot_y=bot_y)
						self.placed_pin_sides_dict[side_name].append((pin, [left_x, bot_y, right_x, top_y], layer))
						side.pop(side.index(pin))

	def _make_subpartitions(self):
		self.partitions = {'left': [],
						   'right': [],
						   'top': [],
						   'bottom': []}
		bounds = {'left': [self.specs['internal_box'][1], self.specs['internal_box'][3]],
				  'right': [self.specs['internal_box'][1], self.specs['internal_box'][3]],
				  'top': [self.specs['internal_box'][0], self.specs['internal_box'][2]],
				  'bottom': [self.specs['internal_box'][0], self.specs['internal_box'][2]]}
		for side in self.partitions.keys():
			self.partitions[side] += self._subpartition_side([bounds[side]], self.placed_pin_sides_dict[side])
		# if self.specs['pg_pin_placement'] == pg_pin_placement_options[2]:
		# 	self.partitions[side] += self._subpartition_side()

	def _subpartition_interval(self, bounds, rect):
		"""Subpartitions a given interval with the given placed pin

		Arguments
		---------
		bounds: list[float, float]
			Lower and upper bound of interval, respectively
		rect: Rectangle object
			Rectangle object occupying dividing space
		"""
		center = rect.center
		layer = rect.layer
		pin_dimensions = rect.coords
		if btwn(center, bounds):
			pitch = self.metals[layer]['pitch']
			direction = self.metals[layer]['direction']
			if direction == 'horizontal':
				lower_interval = [round(bounds[0], 3), round(pin_dimensions[1] - pitch, 3)]
				upper_interval = [round(pin_dimensions[-1] + pitch, 3), round(bounds[1], 3)]
			else:
				lower_interval = [round(bounds[0], 3), round(pin_dimensions[0] - pitch, 3)]
				upper_interval = [round(pin_dimensions[-2] + pitch, 3), round(bounds[1], 3)]
			partitions = [lower_interval, upper_interval]
		else:
			partitions = [bounds]
		return partitions

	def _subpartition_side(self, side_bounds, placed_pins):
		partitions = side_bounds
		for pin in placed_pins:
			pin_obj = pin[0]
			for rect in pin_obj.rects.values():
				center = rect.center
				for partition in partitions:
					if btwn(center, partition):
						new_part = self._subpartition_interval(partition, rect)
						partitions = replace(partitions, new_part, partitions.index(partition))
		return partitions

	def place_interlaced_pg_pins(self, layer, interlace_interval, side_bounds):
		pg_pin_specs = self.specs['pg_pins']
		width = self.metals[layer]['min_width']
		pitch = self.metals[layer]['pitch']
		sides = ['left', 'right'] if self.metals[layer]['direction'] == 'horizontal' else ['top', 'bottom']
		pin_window = width + pitch
		side_length = side_bounds[1] - side_bounds[0]
		interlace_size = round(2 * pg_pin_specs.get('strap_width', width) + pg_pin_specs.get('strap_spacing', pitch), 3)
		interlace_chunk = pin_window * interlace_interval + interlace_size
		n_interlaces = int(np.floor(side_length / interlace_chunk))
		start = side_bounds[0]
		vdd_obj1, vdd_ob2, gnd_obj1, gnd_obj2 = self._get_pg_strap_objs()
		self.power_pin = vdd_obj1
		self.ground_pin = gnd_obj1
		for n in range(n_interlaces):
			vdd_center = round(start + (pin_window * interlace_interval) * n, 3)
			vdd_box, gnd_box = self.draw_pg_strap(vdd_center, vdd_obj1, gnd_obj1, layer=layer, pair=True)
			interlace_list = [(vdd_obj1, vdd_box, layer), (vdd_obj1, vdd_box, layer),
							  (gnd_obj1, gnd_box, layer), (gnd_obj2, gnd_box, layer)]
			for side in sides:
				self.placed_pin_sides_dict[side] += interlace_list

	def _get_pg_strap_objs(self, pair=True):
		pg_pin_dicts = {}
		pg_pin_specs = self.specs['pg_pins']
		vdd_layer = pg_pin_specs['pwr_pin']['layer']
		gnd_layer = pg_pin_specs['gnd_pin']['layer']
		for purpose, pin in self.pg_pins_dict.items():
			pg_pin_dicts[purpose] = {'name': pin,
									 'direction': 'inout',
									 'is_analog': False}
		if self.metals[vdd_layer]['direction'] == 'horizontal':
			vdd_xwidth = round(self.specs['design_boundary'][0], 3)
			vdd_ywidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), 3)
			gnd_xwidth = vdd_xwidth
			gnd_ywidth = vdd_ywidth
		else:
			vdd_ywidth = round(self.specs['design_boundary'][1], 3)
			vdd_xwidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), 3)
			gnd_xwidth = vdd_xwidth
			gnd_ywidth = vdd_ywidth
		side = ['left', 'right'] if pg_pin_specs['strap_orientation'] == 'horizontal' else ['top', 'bottom']
		vdd_obj1 = PHYPortPin(pg_pin_dicts['power_pin'], vdd_layer, side[0], vdd_xwidth, vdd_ywidth)
		gnd_obj1 = PHYPortPin(pg_pin_dicts['ground_pin'], gnd_layer, side[0], gnd_xwidth, gnd_ywidth)
		vdd_obj2 = PHYPortPin(pg_pin_dicts['power_pin'], vdd_layer, side[1], vdd_xwidth, vdd_ywidth)
		gnd_obj2 = PHYPortPin(pg_pin_dicts['ground_pin'], gnd_layer, side[1], gnd_xwidth, gnd_ywidth)
		for obj in [vdd_obj1, gnd_obj1, vdd_obj2, gnd_obj2]:
			self.pins.append(obj)
		return vdd_obj1, gnd_obj1, vdd_obj2, gnd_obj2

	def draw_pg_strap(self, center, pwr_obj, gnd_obj, layer=None, pair=True):
		pg_pin_dicts = {}
		pg_pin_specs = self.specs['pg_pins']
		for purpose, pin in self.pg_pins_dict.items():
			pg_pin_dicts[purpose] = {'name': pin,
									 'direction': 'inout',
									 'is_analog': False}
		vdd_layer = layer if layer else pg_pin_specs['pwr_pin']['layer']
		if self.metals[vdd_layer]['direction'] == 'horizontal':
			vdd_xwidth = round(self.specs['design_boundary'][0], 3)
			vdd_ywidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), 3)
			vdd_pos = round(center - vdd_ywidth / 2, 3)
			if pair:
				pitch = self.specs.get('strap_spacing', self.metals[vdd_layer]['pitch'])
				gnd_xwidth = vdd_xwidth
				gnd_ywidth = vdd_ywidth
				gnd_pos = round(vdd_pos + pitch + vdd_ywidth / 2, 3)
				gnd_center = round(center + pitch + vdd_ywidth / 2, 3)
		else:
			vdd_ywidth = round(self.specs['design_boundary'][1], 3)
			vdd_xwidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), 3)
			vdd_pos = round(center - vdd_xwidth / 2, 3)
			if pair:
				pitch = self.specs.get('strap_spacing', self.metals[vdd_layer]['pitch'])
				gnd_xwidth = vdd_xwidth
				gnd_ywidth = vdd_ywidth
				gnd_pos = round(vdd_pos + pitch + vdd_xwidth / 2, 3)
				gnd_center = round(center + pitch + vdd_ywidth / 2, 3)
		# if not pwr_obj:
		#     pwr_obj = PHYPortPin(pg_pin_dicts['pwr_pin'], vdd_layer, vdd_xwidth, vdd_ywidth, center=center)
		if not pair:
			gnd_layer = layer if layer else pg_pin_specs['gnd_pin']['layer']
			if self.metals[gnd_layer]['direction'] == 'horizontal':
				gnd_xwidth = round(self.specs['design_boundary'][0], 3)
				gnd_ywidth = round(pg_pin_specs.get('strap_width', self.metals[gnd_layer]['min_width']), 3)
				gnd_pos = round(center - gnd_ywidth / 2, 3)
			else:
				gnd_ywidth = round(self.specs['design_boundary'][1], 3)
				gnd_xwidth = round(pg_pin_specs.get('strap_width', self.metals[gnd_layer]['min_width']), 3)
				gnd_pos = round(center - gnd_ywidth / 2, 3)
		# if not gnd_obj:
		#     gnd_obj = PHYPortPin(pg_pin_dicts['gnd_pin'], gnd_layer, gnd_xwidth, gnd_ywidth, center=center)
		pwr_obj.x_width = vdd_xwidth
		pwr_obj.y_width = vdd_ywidth
		gnd_obj.x_width = gnd_xwidth
		gnd_obj.y_width = gnd_ywidth
		if self.metals[vdd_layer]['direction'] == 'horizontal':
			pwr_obj.add_rect(vdd_layer, left_x=0, bot_y=vdd_pos)
			gnd_obj.add_rect(vdd_layer, left_x=0, bot_y=gnd_pos)
		else:
			pwr_obj.add_rect(vdd_layer, left_x=vdd_pos, bot_y=0)
			gnd_obj.add_rect(vdd_layer, left_x=gnd_pos, bot_y=0)
		return pwr_obj.rects[center].coords, gnd_obj.rects[gnd_center].coords

	def place_free_pins(self):
		for side, partitions in self.partitions.items():
			pin_list = self.pin_sides_dict[side]
			for interval in partitions:
				orientation = 'horizontal' if side in ['left', 'right'] else 'veritcal'
				if side == 'left' or side == 'bottom':
					ref_edge = 0
				elif side == 'right':
					ref_edge = self.specs['internal_box'][2]
				elif side == 'top':
					ref_edge = self.specs['internal_box'][3]
				pin_list, placed_pins = self._placement_engine_dispatcher(interval, orientation, ref_edge, pin_list)
				self.placed_pin_sides_dict[side] += placed_pins


	def _placement_engine_dispatcher(self, *args):
		dispatch_dict = {'min_pitch': self._minimum_pitch_engine,
						 'distributed': self._distributed_place_engine,
						 # 'center-span': self._center_span_engine
						 }
		placement_engine = dispatch_dict[self.specs['pin_spacing']]
		return placement_engine(*args)

	def _minimum_pitch_engine(self, interval, orientation, ref_edge, pin_list):
		lower = interval[0]
		placed_pins = []
		while lower < interval[1] and len(pin_list) > 0:
			pin = pin_list.pop()
			if orientation == 'horizontal':
				layer = pin.layer
				width = pin.y_width
				pitch = self.metals[layer]['pitch']
				lower_y = round(lower, 3)
				upper_y = round(lower + width, 3)
				if upper_y > interval[1]:
					return pin_list, placed_pins
				pin.add_rect(layer, left_x=ref_edge, bot_y=lower_y)
				lower = round(upper_y + pitch, 3)
				placed_pins.append(pin)
			else:
				layer = pin.layer
				width = pin.x_width
				pitch = self.metals[layer]['pitch']
				lower_x = round(lower, 3)
				upper_x = round(lower + width, 3)
				if upper_x > interval[1]:
					return pin_list, placed_pins
				pin.add_rect(layer, left_x=lower_x, bot_y=ref_edge)
				lower = round(upper_x + pitch, 3)
				placed_pins.append(pin)
		return pin_list, placed_pins

	def _distributed_place_engine(self, interval, orientation, ref_edge, pin_list):
		interval_size = interval[1] - interval[0]
		# First, check if all pins can fit
		total_pin_width = 0
		min_pin_pitch = 0
		n_pins = len(pin_list)
		for pin in pin_list:
			total_pin_width += pin.y_width if orientation == 'horizontal' else pin.x_width
			min_pin_pitch += self.metals[pin.layer]['pitch']
		all_fit = total_pin_width < interval_size and (interval_size - total_pin_width) >= min_pin_pitch
		# If they all fit with room to spare, then distribute them evenly
		if all_fit:
			space = interval_size - total_pin_width
			interpin_space = round(space / (n_pins - 1), 3)
			lower = interval[0]
			for pin in pin_list:
				layer = pin.layer
				if orientation == 'horizontal':
					width = pin.y_width
					upper = round(lower + width, 3)
					pin.add_rect(layer, left_x=ref_edge, bot_y=lower)
					lower = round(upper + interpin_space)
				else:
					width = pin.x_width
					upper = round(lower + width, 3)
					pin.add_rect(layer, left_x=lower, bot_y=ref_edge)
					lower = round(upper + interpin_space)
			return [], pin_list
		else:
			# If they cannot all fit, then use the minimum pitch placer and return the rest of the list
			return self._minimum_pitch_engine(interval, orientation, ref_edge, pin_list)

	# def _center_span_engine(self, interval, orientation, ref_edge, pin_list, center, span):
	# 	# Sanity check that center is within the interval
	# 	if not btwn(center, interval):





