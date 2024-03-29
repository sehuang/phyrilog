import re
import operator
import ast
import json

class NameLookup(ast.NodeTransformer):
    """NodeTransformer object that replaces all variables in bus index expressions with a corresponding param dictionary
    lookup"""

    def visit_Name(self, node):
        return ast.copy_location(ast.Subscript(
            value=ast.Attribute(value=ast.Name(
                id='self', ctx=ast.Load()),
            attr='params', ctx=ast.Load()),
            slice=ast.Index(value=ast.Str(s=node.id), ctx=ast.Load()),
            ctx=ast.Load()
        ), node)

class WhenWriter(ast.NodeVisitor):

    def __init__(self):
        super().__init__()
        self.when_list = []
        self.sdf_list = []
        self.invert_expr = ""

    def visit_Invert(self, node):
        self.invert_expr = "!"
        # self.when_expr.append("!")
        # self.sdf_expr.append("!")
        self.generic_visit(node)

    # def visit_BitAnd(self, node):
    #     self.when_expr.append("&")
    #     self.sdf_expr.append("&")
    #     self.generic_visit(node)

    def visit_Name(self, node):
        if self.invert_expr:
            node_str = self.invert_expr + node.id
            self.invert_expr = ""
        else:
            node_str = node.id
        self.when_list.append(node_str)
        self.sdf_list.append(node_str)
        self.generic_visit(node)

    def clear(self):
        self.when_list = []
        self.sdf_list = []

    @property
    def when_expr(self):
        return " & ".join(self.when_list)

    @property
    def sdf_expr(self):
        return " & ".join(self.sdf_list)

class NameUpdate(ast.NodeTransformer):

    def __init__(self, suffix):
        super().__init__()
        self.suffix = suffix

    def visit_Name(self, node):
        return ast.copy_location(
            ast.Name(id=node.id + self.suffix, ctx=node.ctx),
            node)


class VerilogModule:
    """Python Object representing a Verilog Module. This will just contain
    Pins

    Parameters
    ----------
    top : str
        The name of the top-level Verilog module that this object will
        represent

    VDD : str, optional
        The related power pin of all pins in the design. Default is 'VDD'.

    VSS : str, optional
        The related ground pin of all pins in the design. Default is 'VSS'.

    filename : str, Path
        The Verilog file name or absolute path.

    constfile : str, Path, optional
        The constants header file name or absolute path.

    clock : Tuple[str], optional
        Iterable of all the possible clock pin names.

    seq_pins : Tuple(Tuple(str, str)), optional
        Iterable of all the sequential pin names with associated clocks.

    Attributes
    ----------
    name : str
        Name of the Verilog Module. Same as top.

    pins : dict
        Dictionary of pin descriptor dictionaries. Keys are pin names,
        values are the dictionaries.

    params : dict
        Dictionary of all extracted parameter values from either the
        constants file or the parameter definition block in the Verilog
        module. Keys are names of parameters, values are parameter values.

    power_pins : dict
        Special dictionary containing the related power and ground pin
        names.

    ports_json_dict : dict
        Dictionary describing all ports of the Verilog module. This is
        passed to the dotlibber.

    """

    def __init__(self, top, VDD='VDD', VSS='VSS', filename=None, constfile=None, clocks=('clock', 'clk'), seq_pins=(('', 'clock', 'when'))):
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
        self.clocks = {}
        self.seq_pins = {}
        self.filename = filename
        self.constfile = constfile
        self.ww = WhenWriter()
        self.pin_name_list = None

        self.top_line_no = self._get_top_module_line_no(line_list, top)
        pin_def_list = self._get_pin_def_list(line_list, self.top_line_no)
        self._check_for_definitions(pin_def_list, self.top_line_no, line_list)
        # self._parse_pin_def_list(pin_def_list)
        self.power_pins = {"power_pin": VDD,
                           "ground_pin": VSS}
        for pin in self.pins.values():
            pin.update(self.power_pins)

        self.ports_json_dict = {'name': self.name,
                                'pins': self.pins}

        self._get_clock(clocks)
        self._get_seq_pins(seq_pins)

    @property
    def pin_names(self):
        if not self.pin_name_list:
            self.pin_name_list = []
            for pin in self.pins.keys():
                self.pin_name_list.append(pin)
        return self.pin_name_list

    @property
    def line_list(self):
        with open(self.filename, 'r') as file:
            line_list = [line.rstrip('\n') for line in file]
        for line in line_list[self.top_line_no:]:
            if 'endmodule' in line:
                end_idx = line_list.index(line) + 1
        return line_list[self.top_line_no:end_idx]

    @property
    def clean_line_list(self):
        return self._strip_comments(self.line_list)

    def _get_top_module_line_no(self, line_list, top):
        """Finds the beginning of the module definition.

        Parameters
        ----------
        line_list : list[str]
            List of lines in the Verilog file.

        top : str
            Name of the top-level Verilog module.

        Returns
        -------
        top_line_no : int
            Index in the file line list of the line containing the
            top-level Verilog module definition (i.e. the line containing
            "module <top>")

        """

        checkstr = "module " + top
        for line in line_list:
            if checkstr in line:
                return line_list.index(line)
        raise NameError(f"Could not find module name {top} in {self.filename}.")

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
        """
        Removes comments and empty lines from line list.

        Parameters
        ----------
        line_list : list[str]
            List of lines in the Verilog file.

        Returns
        -------
        new_line_list : list[str]
            List of lines with comments and empty lines removed.

        """
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
        """
        Do a preliminary check for input/output definitions in the module
        definition.

        Parameters
        ----------
        pin_def_list : list[str]
            List of lines that contain the port declarations.

        top_line_no : int
            Index in the file line list of the line containing the
            top-level Verilog module definition (i.e. the line containing
            "module <top>")

        line_list : list[str]
            List of lines in the Verilog file.

        """
        input_check = ['input' in line for line in pin_def_list]
        output_check = ['output' in line for line in pin_def_list]
        if any(input_check) or any(output_check):
            self._parse_pin_def_list(pin_def_list)
        else:
            self._parse_ports_in_body(top_line_no, line_list)

    def _get_params_and_values(self, pins_str):
        """
        Extracts parameter definitions from string and compiles
        parameter dictionary. Also extracts constants from Verilog header
        files.

        Parameters
        ----------
        pins_str : str
            Joined string containing all port declarations and parameter
            definitions.

        Returns
        -------
        str
            String with only the port direction definitions (parameter
            definitions removed)

        """

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
                    if param_val.isnumeric():
                        self.params[param_name] = int(param_val)

        return pins_str[pins_str.index(params_str) + len(params_str):]

    def _eval_param_op(self, string):
        """Evaluates bus index expression using Abstract Syntax Tree code
         evaluation.

        Parameters
        ----------
        string : str
            Operation string to be evaluated.

        Returns
        -------
        int
           Evaluated result of operation string.

        """

        clean_exp = re.findall(r"[^`\n]+", string)
        clean_exp = "".join(clean_exp)
        expr_ast = ast.parse(clean_exp, mode='eval')
        NameLookup().visit(expr_ast)
        ast.fix_missing_locations(expr_ast)
        return int(eval(compile(expr_ast, filename='<ast>', mode='eval')))

    def _bus_parser(self, bus_idx):
        """Parses bus indices from [X:Y] string. This method can handle
        non-numeric index definitions.

        Parameters
        ----------
        bus_idx : str
            Bus index definition string. This string takes the format
            "[X:Y]" where X and Y are either numeric values or parametrized
             expressions to be evaluated.

        Returns
        -------
        bus_lim_dict : dict
            Dictionary of bus parameters to be added to the pin descriptor
            dictionary.

        """

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
        """Extracts pin list from module definition. This method only works
        if the ports are defined in the module definition.

        Parameters
        ----------
        pin_def_list : list[str]
            List of lines containing port definitions.

        Returns
        -------

        """

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
        """Parse Verilog module body for port definitions. This method is
        invoked if the module definition does not contain port definitions.

        Parameters
        ----------
        top_line_no : int
            Index in the file line list of the line containing the
            top-level Verilog module definition (i.e. the line containing
            "module <top>")

        line_list : list[str]
            List of lines in Verilog module file.

        Returns
        -------

        """
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
        in_pattern = re.compile('^\s*input')
        out_pattern = re.compile('^\s*output')
        end_pattern = re.compile('^\s*endmodule')
        pin_def_list_bk = pin_def_list
        for line in use_line_list:
            if not pin_def_list:
                break
            if re.match(in_pattern, line) or re.match(out_pattern, line):
                def_list.append(line)
                partitions = line.split()
                if partitions[-1] in pin_def_list:
                    pin_def_list.remove(partitions[-1])
            if re.match(end_pattern, line):
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

    def _get_clock(self, clocks):
        """
        Gets clock pin.

        Parameters
        ----------
        clock : str
            Name of clock pin.

        Returns
        -------

        """

        if isinstance(clocks, str):
            clocks = [clocks]
        for clk_name in clocks:
            re_pattern = re.compile(clk_name + "[_\w]*")
            for pin_name in self.pins.keys():
                re_match = re.search(re_pattern, pin_name)
                if re_match:
                    re_name = re_match[0]
                    self.clocks[pin_name] = self.pins[re_name]
                    self.pins[re_name].update({'clock': True})

    def _get_seq_pins(self, seq_pin_names):
        """
        Gets sequential pins.

        Parameters
        ----------
        seq_pin_names : Tuple[str, str, str]
            Tuple of seq name templates to perform RegEx matching.

        Returns
        -------

        """

        for seq_pin in seq_pin_names:
            seq_pin_name = seq_pin[0]
            seq_pin_clk = seq_pin[1]
            seq_pin_when = seq_pin[2]
            re_pattern = re.compile(seq_pin_name + "[_\w]*")
            re_singular = re.compile(seq_pin_name + '*')
            re_clk_suffix_pattern = re.compile("[_\d]")
            for pin_name in self.pins.keys():
                if len(pin_name) == 1:
                    re_match = re.search(re_singular, pin_name)
                else:
                    re_match = re.search(re_pattern, pin_name)
                if re_match:
                    re_name = re_match[0]
                    clk_suffix = re.search(re_clk_suffix_pattern, re_name)
                    clk_suffix = [""] if not clk_suffix else clk_suffix
                    when_ast = ast.parse(seq_pin_when)
                    when_ast = NameUpdate(clk_suffix[0]).visit(when_ast)
                    self.ww.visit(when_ast)
                    when_str = self.ww.when_expr
                    sdf_str = self.ww.sdf_expr
                    self.pins[re_name].update({'sequential': True})
                    self.pins[re_name].update({'related_clock': seq_pin_clk + clk_suffix[0]})
                    self.pins[re_name].update({'when': when_str})
                    self.pins[re_name].update({'sdf_cond': sdf_str})
                    self.seq_pins[pin_name] = self.pins[re_name]
                    self.ww.clear()




    def write_pin_json(self, filename, pin_specs):
        """Serializes self.pins to a JSON file.

        .. deprecated:: 0.9
            'write_pin_json' will be deprecated since this method is
            redundant to self.ports_json_dict

        Parameters
        ----------
        filename : str, Path
            Filename or absolute path to the output JSON.

        pin_specs : dict
            Dictionary of pin specifications

        Returns
        -------

        """
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


