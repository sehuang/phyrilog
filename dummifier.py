from verilog_pin_extract import VerilogModule
import textwrap, re, subprocess, shutil

class DummyModule(VerilogModule):
    def __init__(self, top, outfile, pin_dict):
        self.outfile = outfile
        self.top = top
        self.pin_dict = pin_dict
        self.line_out = ""
        self.write_file()
        super().__init__(top, VDD='VDD', VSS='VSS', filename=outfile, constfile=None, clocks=[('clock')], seq_pins=(''))

    def write_file(self):
        self.line_out += f"module {self.top}(\n"
        i = 1
        for pin in self.pin_dict.keys():
            self.line_out += f"\t{pin} ,\n"
            if i == len(self.pin_dict.keys()):
                self.line_out += f"\t{pin} \n"
        self.line_out = self.line_out + ");\n"
        for pin, attrs in self.pin_dict.items():
            direction = attrs['direction']
            is_bus = attrs['is_bus']
            if is_bus:
                bus_max = attrs['bus_max']
                bus_min = attrs['bus_min']
                self.line_out += f"\t{direction} [{bus_max}:{bus_min}] {pin} ;\n"
            else:
                self.line_out += f"\t{direction} {pin} ;\n"
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
        line_list = self.parent._strip_comments(self.parent.line_list)
        self.line_list = line_list
        end_pttrn = re.compile(r'[\s\S]*\);')
        for macro in self.macros:
            self.dummy_line_lists[macro] = []
            top_line = self._get_dummy_top_line(line_list, macro)
            idx = top_line
            for line in line_list[idx:]:
                self.dummy_line_lists[macro].append(line)
                if ');' in line:
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
                    connection = re.search("[^\(\)]+", connection)[0]
                    self.dummy_pin_dicts[macro][pin_name] = {'name': pin_name,
                                                             'conn': connection}

    def dont_care_about_directions(self):
        for macro, macro_dict in self.dummy_pin_dicts.items():
            for pin_dict in macro_dict.values():
                pin_dict['direction'] = 'input'
                pin_dict['is_bus'] = False

    def get_pin_directions(self, submod_ins = None, submod_outs = None):
        unknowns = []
        for macro, pin_dicts in self.dummy_pin_dicts.items():
            for pin, pin_dict in pin_dicts.items():
                conn = pin_dict['conn']
                connstr = conn.replace('/', '\/')
                connstr = connstr.replace('\\', '\\\\')
                if conn in self.parent.pin_names:
                    pin_dict['direction'] = self.parent.pins[conn]['direction']
                    continue
                collection = []
                for line in self.line_list:
                    if re.search(rf"\({connstr}\)", line):
                        collection.append(line)
                for line in collection:
                    if any([ins in line for ins in submod_ins]):
                        pin_dict['direction'] = 'output'
                    elif any([outs in line for outs in submod_outs]):
                        pin_dict['direction'] = 'input'
                    else:
                        continue
                if not pin_dict.get('direction', None):
                    unknowns.append((macro,pin))
        if len(unknowns):
            for macro, pin in unknowns:
                print(f"WARNING: Could not determine port direction for {macro}.{pin}!")

    def _get_dummy_top_line(self, line_list, dummy):
        pattern = re.compile(fr"[\s]*{dummy} [\w\\\/]+[\s]+\(")
        for line in line_list:
            if re.match(pattern, line):
                return line_list.index(line)