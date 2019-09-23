from LEFBuilder import LEFBuilder
import yaml
import json


class LEFObject:
	def __init__(self, name):
		self.name = name
		self.phys_map = {}

	def add_rect(self, layer, left_x, bot_y, right_x, top_y):
		if layer in self.phys_map.keys():
			self.phys_map[layer]['coord'].append = [left_x, bot_y, right_x, top_y]
		else:
			self.phys_map[layer]['coord'] = [[left_x, bot_y, right_x, top_y]]

	# self.phys_map[layer]['shape'] = 'RECT'

	def write_lef_block(self):
		pass


class LEFPortPin(LEFObject):
	def __init__(self, pin_dict, bus_idx=None):
		super().__init__(None)

		self.pin_dict = pin_dict
		self.name = pin_dict['name']
		self.direction = pin_dict['direction']
		self.type = 'SIGNAL'
		# self.is_bus = pin_dict.get("is_bus", False)
		if bus_idx:
			self.bus_idx = bus_idx
		self.block_structure = {}

	def write_lef_block_struct(self, bus_idx=None):
		direction_str = f"DIRECTION {self.direction} ;"
		type_str = f"USE SIGNAL ;"
		if not self.is_bus:
			pin_def_str = f"PIN {self.name}"
		else:
			pin_def_str = f"PIN {self.name}[{bus_idx}]"


class LEFDesign:
	"""Python representation of a LEF Design. Right now this just consumes VerilogModules"""

	def __init__(self, verilog_module, techfile, xwidth=None, ywidth=None,
				 aspect_ratio=[1, 1], spec_dict=None):
		self.verilog_pin_dict = verilog_module.pins
		self.name = verilog_module.name

		filetype = techfile.split('.')[-1].lower()  # This normally expects a HAMMER tech.json
		with open(techfile) as file:
			if filetype == 'json':
				self.tech_dict = json.load(file)
			elif filetype == 'yaml' or filetype == 'yml':
				raise NotImplementedError
			else:
				raise ValueError(f"Unrecognized File Type .{filetype}")

		self.metals = self.tech_dict['stackups'][0]['metals']
		self.spec_dict = spec_dict
		self.x_width = xwidth
		self.y_width = ywidth
		self.aspect_ratio = aspect_ratio
		self.pins = {}

	def add_pin_objects(self):
		self.n_inputs = 0
		self.n_outputs = 0
		for pin_name, pin_info in self.verilog_pin_dict.items():
			pin_side = self.spec_dict['pins'][pin_name].get('side', None)
			if pin_info.get('is_bus',None):
				self.n_inputs += (pin_info['direction'] == 'input') * (pin_info['bus_max']+1)
				self.n_outputs += (pin_info['direction'] == 'output') * (pin_info['bus_max']+1)
				for pin in range(pin_info['bus_max']+1):
					self.pins[pin_name + '_' + str(pin)] = LEFPortPin(pin_info, bus_idx=pin)
			else:
				self.n_inputs += pin_info['direction'] == 'input'
				self.n_outputs += pin_info['direction'] == 'output'
				self.pins[pin_name] = LEFPortPin(pin_info)

	def define_design_boundaries(self):
		pass

class BBoxLEF(LEFDesign):
	"""Black-boxed LEF object. This class describes LEF stuff"""

	# def __init__(self, verilog_module, techfile: str, xwidth=None, ywidth=None,
	# 			 aspect_ratio=[1, 1], spec_dict=None):
	def __init__(self,*args,**kwargs):
		super().__init__(*args, *kwargs)

		self.add_pin_objects()

	def define_design_boundaries(self):
		if self.x_width:
			x_width = self.x_width
		elif self.y_width:
			x_width = self.y_width * self.aspect_ratio[1] / self.aspect_ratio[0]
		else:
			self.x_width = None # Wait until later to figure this out

		if self.y_width:
			y_width = self.y_width
		elif self.y_width:
			y_width = self.x_width * self.aspect_ratio[0] / self.aspect_ratio[1]
		else:
			self.y_width = None # Wait until later to figure this out

		self.input_side =  self.spec_dict.get('input_side', 'left')
		self.output_side = self.spec_dict.get('output_side', 'left')