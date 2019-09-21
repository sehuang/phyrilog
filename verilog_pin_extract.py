import re
import operator

class VerilogModule:
	"""Python Object representing a Verilog Module. This will just contain Pins"""

	def __init__(self, top, VDD='VDD', VSS='VSS', filename=None, constfile=None, module=None):
		if not filename:
			if not module:
				raise NameError("Please provide a module.")
			else:
				name = top
		else:
			with open(filename, 'r') as file:
				line_list = [line.rstrip('\n') for line in file]
			if constfile:
				with open(constfile, 'r') as file:
					self.constfile_list =  self._strip_comments([line.rstrip('\n') for line in file])
			else:
				self.constfile_list = None

		self.name = top
		self.pins = {}
		self.params = {}
		self.op_lut = {"+": operator.add,
					   "-": operator.sub,
					   "*": operator.mul,
					   "/": operator.floordiv}

		top_line_no = self._get_top_module_line_no(line_list, top)
		pin_def_list = self._get_pin_def_list(line_list, top_line_no)
		self._parse_pin_def_list(pin_def_list)
		self.power_pins = {"power_pin": VDD,
						   "ground_pin": VSS}
		for pin in self.pins.values():
			pin.update(self.power_pins)

		self.ports_json_dict = {'name': self.name,
								'pins': self.pins}

	def _get_top_module_line_no(self, line_list, top):
		checkstr = "module " + top
		for line in line_list:
			if checkstr in line:
				return line_list.index(line)

	def _get_pin_def_list(self, line_list, top_line_no):
		for line in line_list[top_line_no:]:
			if ");" in line:
				end_idx = line_list.index(line) + 1
				break
		pin_def_list = self._strip_comments(line_list[top_line_no:end_idx])
		return pin_def_list

	def _strip_comments(self, line_list):
		new_line_list = []
		for line in line_list:
			if re.search("//",line):
				continue
			elif re.match("(?![\s\S])",line):
				continue
			else:
				new_line_list.append(line)
		return new_line_list

	def _get_params_and_values(self, pins_str):
		params_str = re.findall(r"(?<=#\().*(?=\)\()", pins_str)
		if len(params_str) > 0:
			params_str = params_str[0]
			params_list = params_str.split(',')
			for param in params_list:
				parts = param.split()
				param_name = parts[1]
				param_val = re.findall(r'\d',parts[-1])[0]
				self.params[param_name] = param_val
		else:
			params_str = ""
		if self.constfile_list:
			for line in self.constfile_list:
				parts = line.split()
				if parts[0] == '`define':
					param_name = parts[1]
					param_val = parts[-1]
					self.params[param_name] = param_val

		return pins_str[pins_str.index(params_str) + len(params_str):]

	def _bus_parser(self, bus_idx):
		# bus_idx = re.findall(r"\[\w+:\w+\]", pin_str)[0]
		limits = bus_idx[1:-1].split(":")
		if not limits[0].isdigit():
			try:
				bus_max = self.params[limits[0]]
			except KeyError:
				try:
					left_exp = re.findall(r"[\w]+(?=[+\-*/])", limits[0])[0]
					right_exp = re.findall(r"(?<=[+\-*/])[\w]+", limits[0])[0]
					operator = re.findall(r"[+\-*/]", limits[0])[0]
					left_exp = self.params[left_exp] if not left_exp.isdigit() else left_exp
					right_exp = self.params[right_exp] if not right_exp.isdigit() else right_exp
					bus_max = self.op_lut[operator](int(left_exp), int(right_exp))
				except KeyError:
					raise KeyError("Parameter " + limits[0] + " is not defined.")
		else:
			bus_max = limits[0]
		if not limits[1].isdigit():
			try:
				bus_min = self.params[limits[1]]
			except KeyError:
				try:
					left_exp = re.findall(r"[\w]+(?=[+\-*/])", limits[1])[0]
					right_exp = re.findall(r"(?<=[+\-*/])[\w]+", limits[1])[0]
					operator = re.findall(r"[+\-*/]", limits[1])[0]
					left_exp = self.params[left_exp] if not left_exp.isdigit() else left_exp
					right_exp = self.params[right_exp] if not right_exp.isdigit() else right_exp
					bus_min = self.op_lut[operator](int(left_exp), int(right_exp))
				except KeyError:
					raise KeyError("Parameter " + limits[0] + " is not defined.")
		else:
			bus_min = limits[1]

		bus_lim_dict = {"is_bus": True,
						"bus_max": bus_max,
						"bus_min": bus_min, }
		return bus_lim_dict

	def _parse_pin_def_list(self, pin_def_list):
		if len(pin_def_list) == 1:
			pins_str = pin_def_list[0]
		else:
			pins_str = ''
			for pin in pin_def_list:
				pins_str += pin
		pins_str = self._get_params_and_values(pins_str)
		pins_str_match = re.findall(r"(?<=\().*(?=\))", pins_str)[0]
		pins_str_list = pins_str_match.split(',')
		for pin in pins_str_list:
			parts = pin.split()
			direction = parts[0]
			# name = re.match(r'\w', parts[-1]).string
			name = parts[-1]
			bus_idx = re.findall(r"\[.*\]", pin)
			is_bus = len(bus_idx) > 0
			pin_info = {"name": name,
						"direction": direction,
						"is_analog": False
						}
			if is_bus:
				bus_lim_dict = self._bus_parser(bus_idx[0])
				pin_info.update(bus_lim_dict)

			self.pins[name] = pin_info
