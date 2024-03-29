from verilog_pin_extract import VerilogModule
import textwrap, re

class DummyModule(VerilogModule):
    def __init__(self, top, outfile, pin_dict):
        self.outfile = outfile
        self.top = top
        self.pin_dict = pin_dict
        self.line_out = ""
        self.write_file()
        super().__init__(top, VDD='VDD', VSS='VSS', filename=outfile, constfile=None, clocks=[('clock')], seq_pins=[()])

    def write_file(self):
        self.line_out += f"module {self.top}(\n"
        for pin in self.pin_dict.keys():
            self.line_out += f"\t{pin},\n"
        self.line_out = self.line_out[-2] + ");\n"
        for pin, attrs in self.pin_dict.items():
            direction = attrs['direction']
            is_bus = attrs['is_bus']
            if is_bus:
                bus_max = attrs['bus_max']
                bus_min = attrs['bus_min']
                self.line_out += f"\t{direction} [{bus_max}:{bus_min}] {pin};\n"
            else:
                self.line_out += f"\t{direction} {pin};\n"
        self.line_out += "endmodule"
        with open(self.outfile, 'w') as file:
            file.write(self.line_out)

class Dummifier:
    def __init__(self, parent_module, macros=None):
        self.parent = parent_module
        self.macros = macros
        self.dummies = []
        self.dummy_line_lists = {}
        self.dummy_pin_dicts = {}

    def scrape_dummies(self):
        line_list = self.parent.line_list
        self.line_list = line_list
        end_pttrn = re.compile(r'[\s\S]*\);')
        for macro in self.macros:
            self.dummy_line_lists[macro] = []
            top_line = self._get_dummy_top_line(line_list, macro)
            idx = top_line
            for line in line_list[idx:]:
                self.dummy_line_lists[macro].append(line)
                if re.match(end_pttrn, line):
                    end_line = line_list.index(line)
                    break

    def get_macro_pins(self):
        pattern = re.compile("\([\s\S]+\)[,]*")
        for macro, macro_line_list in self.dummy_line_lists.items():
            self.dummy_pin_dicts[macro] = {}
            for macro_line in macro_line_list:
                if re.search(pattern, macro_line):
                    pin_name = macro_line.split("(")[0].strip()[1:]
                    connection = re.search(pattern, macro_line)[0]
                    connection = re.search("[^\(\)]", connection)[0]
                    self.dummy_pin_dicts[macro][pin_name] = {'name': pin_name,
                                                             'conn': connection}

    def get_pin_directions(self, submod_ins = None, submod_outs = None):
        unknowns = []
        for macro, pin_dicts in self.dummy_pin_dicts.items():
            for pin, pin_dict in pin_dicts.items():
                conn = pin_dict['conn']
                if conn in self.parent.pin_names:
                    pin_dict['direction'] = self.parent.pins[conn]['direction']
                    continue
                collection = []
                for line in self.line_list:
                    if re.search(f"\({pin_dict['conn']}\)", line):
                        collection.append(line)
                for line in collection:
                    if any([ins in line for ins in submod_ins]):
                        pin_dict['direction'] = 'output'
                    elif any([outs in line for outs in submod_outs]):
                        pin_dict['direction'] = 'input'
                    elif 'assign' in line:
                        lin = line.replace('assign', "")

                    else:
                        continue
                if not pin_dict.get('direction', None):
                    unknowns.append((macro,pin))
        if len(unknowns):
            for macro, pin in unknowns:
                print(f"WARNING: Could not determine port direction for {macro}.{pin}!")

    def _get_dummy_top_line(self, line_list, dummy):
        pattern = re.compile(fr"[\s]*{dummy} [\w]+ \(")
        for line in line_list:
            if re.match(pattern, line):
                return line_list.index(line)


class BinaryOp:
    def __init__(self, left_op, right_op):
        self.left_op = left_op
        self.right_op = right_op

class Equals(BinaryOp):
    def __init__(self, left_op, right_op):
        super().__init__(left_op, right_op)


class Logic(BinaryOp):
    def __init__(self, left_op, right_op, operator):
        super().__init__(left_op, right_op)

    def _parse_op(self, operator):
        if operator == '|':
            self.operation = 'OR'
        elif operator == '&':
            self.operation = 'AND'
        elif operator == '^':
            self.operation = 'XOR'

class AssignOp:
    def __init__(self, expression):
        self.expression = expression

    def parse_expression(self):
        if 'assign' in self.expression:
            self.expression.replace('assign', '')
