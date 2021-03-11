from scripts.asap7.get_srams import SRAMList
from libraries.bbox_libs import *
import shutil
from LIBBuilder import *
from GDSBuilder import *
from utilities import *
import numpy as np

class SRAMBBox:
    """This object is a wrapper for all the generators and views2 associated with a single SRAM BBox instance."""

    def __init__(self, name, modulefile, constfile, techfile, layermapfile, cornerfile, views_dir, characterizer=None):
        self.name = name
        self.per_word_bit_xwidth =  0.22 # This was determined arbitrarily.
        self.clock_names = (('CE'),)
        self.seq_names = (('O[^A-Z]','CE','~OEB'),('I[^A-Z]','CE','~CSB & ~WEB'),('A[^A-Z]','CE','~CSB'))
        self.verilog_module = VerilogModule(name, filename=modulefile, constfile=constfile,
                                            clocks=self.clock_names, seq_pins=self.seq_names)
        self.layermapfile = layermapfile
        self.cornerfile = cornerfile
        self.specs = {'pin_margin': True,
                      'site': 'coreSite',
                      'port_sides': {'input': 'left',
                                     'output': 'left'},
                      'pin_spacing': 'min_pitch',
                      'pg_pins': {
                          'pg_pin_placement': 'interlaced',
                          'interlace_interval': 8,
                          'interlace_orientation': 'horizontal',
                          'h_layer': 'M4',
                          'v_layer': 'M5',
                          'pwr_pin': {
                              'layer': 'M4',
                              'side': 'left',
                          },
                          'gnd_pin': {
                              'layer': 'M4',
                              'side': 'left',
                          },
                      },
                      'exclude_layers': ['M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'Pad']}
        self.pin_specs = {'pins': {'h_layer': 'M4',
                                   'v_layer': 'M5',
                                   'pin_length': 1
                                   },
                          'pg_pins': {
                              'pg_pin_placement': 'interlaced',
                              'interlace_interval': 8,
                              'strap_orientation': 'horizontal',
                              'h_layer': 'M4',
                              'v_layer': 'M5',
                              'pwr_pin': {
                                  'layer': 'M4',
                                  'side': 'left',
                              },
                              'gnd_pin': {
                                  'layer': 'M4',
                                  'side': 'left',
                              },
                          },}
        self.specs = r_update(self.specs, self.pin_specs)
        if 'wordLength' not in self.verilog_module.params.keys() \
                or 'numAddr' not in self.verilog_module.params.keys():
            self._get_xwidth_from_name()
        else:
            self._get_xwidth_from_consts()
        self.lib_options = {'capacitive_load_unit': '(1, ff)',
                            'time_unit': '1ps'}
        if characterizer:
            self.characterizer = characterizer(self.word_length, self.num_addr)
        else:
            self.characterizer = None
        self.phy = BBoxPHY(self.verilog_module, techfile, spec_dict=self.specs)

        views_dir_path = pathlib.Path(os.path.abspath(views_dir))
        if not os.path.exists(views_dir_path):
            os.mkdir(views_dir_path)
        self.lef_file_path = views_dir_path / 'lef'
        self.gds_file_path = views_dir_path / 'gds'
        self.lib_file_path = views_dir_path / 'lib'
        if not os.path.exists(self.lef_file_path):
            os.mkdir(self.lef_file_path)
        if not os.path.exists(self.gds_file_path):
            os.mkdir(self.gds_file_path)
        if not os.path.exists(self.lib_file_path):
            os.mkdir(self.lib_file_path)

    def build_lef(self, path=None):
        self.lef_builder = BBoxLEFBuilder(self.phy, indent_char_width=2)
        if path:
            filepath = path
        else:
            filepath = self.lef_file_path / (self.name + '.lef')
        self.lef_builder.write_lef(filename=filepath)

    def build_gds(self, path=None):
        self.gds_builder = GDSDesign(self.phy, layermap_file=self.layermapfile)
        self.gds_builder.add_polygons()
        if path:
            filepath = path
        else:
            filepath = self.gds_file_path / (self.name + '.gds')
        self.gds_builder.write_gdsfile(filename=filepath)

    def build_lib(self, path=None):
        self.lib_builder = LIBBuilder(self.phy, corners=self.cornerfile, characterizer=self.characterizer,
                                      options=self.lib_options)
        if path:
            filepath = path
        else:
            filepath = self.lib_file_path / (self.name + '_lib')
        self.lib_builder.write_lib(filepath)

    def build_all(self, lef_path=None, gds_path=None, lib_path=None):
        print(f'Building {self.name} phy views...')
        self.build_lef(path=lef_path)
        self.build_gds(path=gds_path)
        self.build_lib(path=lib_path)
        print("\n")

    def build_all_xN(self, N, lef_path=None, gds_path=None, lib_path=None, build_lib=False):
        self.phy.scale(N)
        self.name = self.name + f'_x{N}'
        print(f'Building {self.name} phy views...')
        self.build_lef(path=lef_path)
        self.build_gds(path=gds_path)
        if build_lib:
            self.build_lib(path=lib_path)
        self.name = self.name[:-2]
        self.phy.scale(1 / N)
        print('\n')

    def _get_xwidth_from_consts(self):
        self.word_length = int(self.verilog_module.params['wordLength'])
        self.num_addr = int(self.verilog_module.params['numAddr'])
        aratio_limit = 2.5
        diff = 1
        long_dim = max(2 ** self.num_addr, self.word_length)
        short_dim = min(2 ** self.num_addr, self.word_length)
        aratio = round(long_dim / short_dim, 2)
        if aratio > aratio_limit:
            diff = np.rint(np.sqrt(aratio / aratio_limit))
            aratio = round(long_dim / (short_dim * diff ** 2), 2)

        xwidth = self.per_word_bit_xwidth * int(short_dim)
        self.specs['x_width'] = round(xwidth * diff, 3)
        self.specs['aspect_ratio'] = [1, aratio]
        print(f'Xwidth: {round(xwidth * diff, 3)}')
        print(f'Aspect Ratio: {aratio}')

    def _get_xwidth_from_name(self):
        num_locs = re.search(r"[\d]+(?=x)", self.name)[0]
        word_len = re.search(r"(?<=x)[\d]+", self.name)[0]
        num_addr = str(int(np.log2(int(num_locs))))
        self.verilog_module.params['wordLength'] = word_len
        self.verilog_module.params['numAddr'] = str(num_addr)
        self._get_xwidth_from_consts()


class ASAP7Characterizer(Characterizer):

    def __init__(self, wordLength, numAddr):
        self.word_length = wordLength
        self.num_addr = numAddr

    def characterizer(self, arc_type, timing_type, pin, related_pin, corner, params):
        # SetupArc
        # For simplicity make rise & fall equal
        if timing_type == 'setup_rising':
            if corner.name == 'PVT_0P63V_100C':
                R = 40
                i1 = 1.06
                i2 = 0.98
            else:
                R = 23
                i1 = 1.04
                i2 = 0.97
            time = R * i1**np.log(params['related_pin_transition']) * i2**np.log(params['constrained_pin_transition']) * (1 + self.num_addr/10)
            return round(float(time), 4)

        # HoldArc
        # For simplicity make rise & fall equal
        elif timing_type == 'hold_rising':
            if corner.name == 'PVT_0P63V_100C':
                R = 18
                i1 = 0.9
                i2 = 1.15
            else:
                R = 12
                i1 = 0.85
                i2 = 1.1
            time = R * i1**np.log(params['related_pin_transition']) * i2**np.log(params['constrained_pin_transition']) * (1 + self.num_addr/10)
            return round(float(time), 4)

        # ClockToQArc
        # For simplicity make rise & fall equal (dominated by sense amp)
        elif arc_type == 'cell_rise' or arc_type == 'cell_fall':
            if corner.name == 'PVT_0P63V_100C':
            	R = 50
            	i1 = 1.05
            	i2 = 1.15
            else:
                R = 30
                i1 = 1.02
                i2 = 1.1
            time = R * i1**np.log(10*params['input_net_transition']) * i2**np.log(10*params['total_output_net_capacitance']) * (1 + self.num_addr/10)
            return round(float(time), 4)
        elif arc_type == 'rise_transition' or arc_type == 'fall_transition':
            # Indices seem backwards in this calculation
            if corner.name == 'PVT_0P63V_100C':
                R = 0.75
                i1 = 1.75
                i2 = 1.01
            else:
                R = 0.5
                i1 = 1.65
                i2 = 1.01
            time = R * i1**np.log(10*params['input_net_transition']) * i2**np.log(10*params['total_output_net_capacitance']) * (1 + self.num_addr/10)
            return round(float(time), 4)
        else:
            return round(float(5.0), 4)
            
        pass


class ASAP7SRAMs:
    """This class is a container for all the ASAP7 SRAM black box views."""

    def __init__(self, behav_file, project_dir, hammer_dir, listfile=None, search=None):

        self.project_dir = project_dir
        self.layermapfile = project_dir / 'resources/asap7_TechLib.layermap'
        self.techfile = hammer_dir / 'src/hammer-vlsi/technology/asap7/asap7.tech.json'
        self.cornerfile = project_dir / 'resources/asap7_lib_corners.json'

        self.sramlist = SRAMList(behav_file, listfile)
        if search:
            self.sramlist.search(search)
        self.srams_names = self.sramlist.srams
        self.srams = []
        with open(behav_file, 'r') as file:
            self.line_list = [line.rstrip('\n') for line in file]
        self.line_list = self._strip_comments(self.line_list)
        # self.module_def_list = [line for line in self.line_list if "module" in line]
        if os.path.exists('tmp'):
            shutil.rmtree('tmp')


    def _strip_comments(self, line_list):
        """Removes comments from lines."""
        new_line_list = []
        multiline_comment = False

        # Precompile RegEx patterns
        slineA = re.compile("//")
        slineB = re.compile("/\*[\w\W]+\*/")
        mline_begin = re.compile("/\*")
        mline_end =  re.compile("\*/")
        empty = re.compile("(?![\s\S])")

        # Line-by-line Comment Filter
        for line in line_list:
            # Remove single line comment
            if re.search(slineA, line):
                continue
            # Remove single line comment defined with /* ... */ syntax
            elif re.match(slineB, line):
                continue
            # Remove first line of multiline comment and begin tracking
            elif re.search(mline_begin, line):
                multiline_comment = True
                continue
            # Remove lines that are in the body of the multiline comment
            elif multiline_comment and not re.search(mline_end, line):
                continue
            # Remove last line of multiline commend and stop tracking
            elif re.search(mline_end, line):
                multiline_comment = False
                continue
            # Remove empty lines
            elif re.match(empty, line):
                continue
            else:
                new_line_list.append(line)
        return new_line_list

    def _find_module(self, top):
        for line in self.line_list:
            if top in line.split() and 'module' in line.split():
                return self.line_list.index(line)

    def _get_relevant_lines(self, top):
        os.chdir('tmp')
        top_line = self._find_module(top)
        idx = top_line - 1
        line = self.line_list[idx]
        premodule_block = []
        while line != 'endmodule' and idx > 0:
            premodule_block.insert(0, line)
            idx += -1
            line = self.line_list[idx]
        module_block = []
        idx = top_line
        line = self.line_list[idx]
        while line != 'endmodule':
            line = self.line_list[idx]
            module_block.append(line)
            idx += 1
        self.modulefile = "temp_module_file.v"
        with open(self.modulefile, "w+") as modulefile:
            for line in module_block:
                modulefile.write(f"{line}\n")
        self.constfile = "temp_const_file.vh"
        with open(self.constfile, "w+") as constfile:
            for line in premodule_block:
                constfile.write(f"{line}\n")
        os.chdir('..')

    def make_sram_objs(self, name):
        if not os.path.exists(self.project_dir / 'views'):
            os.mkdir(self.project_dir / 'views')
        self.srams.append(SRAMBBox(name, self.modulefile, self.constfile, self.techfile,
                                   self.layermapfile, self.cornerfile, self.project_dir / 'views',
                                   characterizer=ASAP7Characterizer))


    def build_all_sram_views(self, sram_obj):
        sram_obj.build_all()
        sram_obj.build_all_xN(4)

    def add_all_srams(self):
        for sram_name in self.srams_names:
            print(f'Building {sram_name} PHYObject...')
            os.mkdir('tmp')
            self._get_relevant_lines(sram_name)
            os.chdir('tmp')
            self.make_sram_objs(sram_name)
            os.chdir('..')
            shutil.rmtree('tmp')
            print("\n")

    def build_all_srams(self):
        for sram_obj in self.srams:
            self.build_all_sram_views(sram_obj)

