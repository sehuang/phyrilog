import re
import operator
import json

class VerilogModule:
    """Python Object representing a Verilog Module. This will just contain Pins"""

    def __init__(self, top, VDD='VDD', VSS='VSS', filename=None, constfile=None):
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
        self._check_for_definitions(pin_def_list, top_line_no, line_list)
        # self._parse_pin_def_list(pin_def_list)
        self.power_pins = {"power_pin": VDD,
                           "ground_pin": VSS}
        for pin in self.pins.values():
            pin.update(self.power_pins)

        self.ports_json_dict = {'name': self.name,
                                'pins': self.pins}

    def _get_top_module_line_no(self, line_list, top):
        """Finds the beginning of the module definition."""

        checkstr = "module " + top
        for line in line_list:
            if checkstr in line:
                return line_list.index(line)
        raise NameError(f"Could not find module name {top} in file.")

    def _get_pin_def_list(self, line_list, top_line_no):
        """Returns list of strings containing the module and port definitions."""

        for line in line_list[top_line_no:]:
            if ");" in line:
                end_idx = line_list[top_line_no:].index(line)
                break
        if end_idx == 0:
            end_idx += 1 # THIS IS A HACK, DO THIS BETTER NEXT TIME
        pin_def_list = self._strip_comments(line_list[top_line_no:top_line_no + end_idx])
        return pin_def_list

    def _strip_comments(self, line_list):
        """Removes comments from lines."""
        new_line_list = []
        multiline_comment = False
        for line in line_list:
            if re.search("//", line):
                continue
            elif re.match("/\*[\w\W]+\*/", line):
                continue
            elif re.search("/\*", line):
                multiline_comment = True
                continue
            elif multiline_comment and not re.search("\*/", line):
                continue
            elif re.search("\*/", line):
                multiline_comment = False
                continue
            elif re.match("(?![\s\S])", line):
                continue
            else:
                new_line_list.append(line)
        return new_line_list

    def _check_for_definitions(self, pin_def_list, top_line_no, line_list):
        input_check = ['input' in line for line in pin_def_list]
        output_check = ['output' in line for line in pin_def_list]
        if any(input_check) or any(output_check):
            self._parse_pin_def_list(pin_def_list)
        else:
            self._parse_ports_in_body(top_line_no, line_list)

    def _get_params_and_values(self, pins_str):
        """Extracts parameter definitions from string and compiles parameter dictionary.
        Also extracts constants from Verilog header files."""

        params_str = re.findall(r"(?<=#\().*(?=\)[\s]*\()", pins_str)
        if len(params_str) > 0:
            params_str = params_str[0]
            params_list = params_str.split(',')
            for param in params_list:
                parts = param.split()
                param_name = parts[1]
                param_val = re.findall(r'\d+',parts[-1])[0]
                self.params[param_name] = int(param_val)
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

    def _eval_param_op(self, string):
        """Evaluates operation for bus indices when netlist uses parameters. This method
        recurs until it runs out of string to try evaluating"""

        left_exp = re.findall(r"[\S]+(?=(?:[\s]*[+\-*/]))", string)
        if len(left_exp) == 0:
            raise KeyError(f"Parameter {string} not defined.")
        left_exp = re.findall(r"[^`]+", left_exp[0]) 			# get rid of tick
        right_exp = re.findall(r"(?<=[+\-*/])[\s]*[\S]+", string)
        if len(right_exp) == 0:
            raise KeyError(f"Parameter {string} not defined.")
        right_exp = re.findall(r"[\S]+", right_exp[0])
        operator = re.findall(r"[+\-*/]", string)[0]
        if len(left_exp) == 0 or len(right_exp) == 0:
            raise KeyError(f"Parameter {string} not defined.")
        else:
            left_exp = left_exp[0]
            right_exp = right_exp[0]
        try:
            left_exp = self.params[left_exp] if not left_exp.isdigit() else left_exp
        except KeyError: # This might itself be another operation!
            left_exp = self._eval_param_op(left_exp)
        try:
            right_exp = self.params[right_exp] if not right_exp.isdigit() else right_exp
        except KeyError: # This might itself be another operation!
            right_exp = self._eval_param_op(right_exp)
        index = self.op_lut[operator](int(left_exp), int(right_exp))
        return index


    def _bus_parser(self, bus_idx):
        """Parses bus indices from [X:Y] string. This method can handle non-numeric
        index definitions."""

        limits = bus_idx[1:-1].split(":")
        if not limits[0].isdigit():
            try:
                bus_max = self.params[limits[0]]
            except KeyError: # Max index is probably an operation
                bus_max = self._eval_param_op(limits[0])
        else:
            bus_max = int(limits[0])
        if not limits[1].isdigit():
            try:
                bus_min = self.params[limits[1]]
            except KeyError: # Min index is probably an operation
                bus_min = self._eval_param_op(limits[1])
        else:
            bus_min = int(limits[1])

        bus_lim_dict = {"is_bus": True,
                        "bus_max": bus_max,
                        "bus_min": bus_min, }
        return bus_lim_dict

    def _parse_pin_def_list(self, pin_def_list):
        """Extracts pin list from string and compiles pin dictionary."""

        if len(pin_def_list) == 1:
            pins_str = pin_def_list[0]
        else:
            pins_str = ''
            for pin in pin_def_list:
                pins_str += pin
        pins_str = self._get_params_and_values(pins_str)
        pins_str_match = re.findall(r"(?<=\().*", pins_str)
        if len(pins_str_match) == 0:
            pins_str_match = re.findall(r"(?<=\)\().*", pins_str)
        pins_str_list = pins_str_match[0].split(',')

        for pin in pins_str_list:
            parts = pin.split()
            try:
                direction = parts[0]
            except:
                continue
            # name = re.match(r'\w', parts[-1]).string
            name = parts[-1]
            bus_idx = re.findall(r"\[.*\]", pin)
            is_bus = len(bus_idx) > 0
            names = []
            for part in parts[1:]:
                if '[' in part or ']' in part:
                    continue
                else:
                    names.append(part)
            for name in names:
                pin_info = {"name": name,
                            "direction": direction,
                            "is_analog": False
                            }
                if is_bus:
                    bus_lim_dict = self._bus_parser(bus_idx[0])
                    pin_info.update(bus_lim_dict)

                self.pins[name] = pin_info

    def _parse_ports_in_body(self, top_line_no, line_list):
        use_line_list = line_list[top_line_no:]
        pin_def_list = self._get_pin_def_list(line_list, top_line_no)
        if len(pin_def_list) == 1:
            pins_str = pin_def_list[0]
        else:
            pins_str = ''
            for pin in pin_def_list:
                pins_str += pin
        pins_str = self._get_params_and_values(pins_str)
        # pins_str_match = re.findall(r"(?<=\().*", pins_str)
        # if len(pins_str_match) == 0:
        #     pins_str_match = re.findall(r"(?<=\)\().*", pins_str)
        # pins_str_list = pins_str_match[0].split(',')

        def_list = []
        for line in use_line_list:
            if 'input' in line or 'output' in line:
                def_list.append(line)
            if 'endmodule' in line:
                break

        for pin in def_list:
            parts = pin.split()
            # name = re.match(r'\w', parts[-1]).string
            # name = parts[-1]
            direction = parts[0]
            bus_idx = re.findall(r"\[.*\]", pin)
            is_bus = len(bus_idx) > 0
            names = []
            for part in parts[1:]:
                if '[' in part or ']' in part:
                    continue
                else:
                    names.append(part)
            for name in names:
                name = re.sub('[\W]+', '', name)
                pin_info = {"name": name,
                            "direction": direction,
                            "is_analog": False
                            }
                if is_bus:
                    bus_lim_dict = self._bus_parser(bus_idx[0])
                    pin_info.update(bus_lim_dict)

                self.pins[name] = pin_info

    def write_pin_json(self, filename, pin_specs):
        json_dict = {'name': self.name,
                     'revision': 0,
                     'cells': [{'name': self.name,
                               'pins': [],
                               'pg_pins': []}],
                     }
        all_pins_specs = pin_specs['all_pins']
        for pin_name, pin_dict in self.pins.items():
            this_pin_specs = pin_specs.get(pin_name, dict())
            pin_dict.update(all_pins_specs)
            pin_dict.update(this_pin_specs) # specific pin specs take precedence
            # pin_dict['related_power_pin'] = pin_dict.pop('power_pin')
            # pin_dict['related_ground_pin'] = pin_dict.pop('ground_pin')
            json_dict['cells'][0]['pins'].append(pin_dict)
            pg_pins = [{'name': self.power_pins['power_pin'],
                        'pg_type': 'primary_power'},
                       {'name': self.power_pins['ground_pin'],
                        'pg_type': 'primary_ground'},
                       ]
            json_dict['cells'][0]['pg_pins'] = pg_pins

            with open(filename, 'w') as json_file:
                json.dump(json_dict,json_file)


