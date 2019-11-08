from scripts.get_srams import SRAMList
from libraries.bbox_libs import *
import tempfile
import os
import pathlib
import shutil
from verilog_pin_extract import VerilogModule
from verilog2phy import *
from LIBBuilder import *
from GDSBuilder import *
from LEFBuilder import *
from utilities import *

class SRAMBBox:
    """This object is a wrapper for all the generators and views2 associated with a single SRAM BBox instance."""

    def __init__(self, name, modulefile, constfile, techfile, layermapfile, cornerfile, views_dir):
        self.name = name
        self.per_word_bit_xwidth =  0.538 # This was determined arbitrarily.
        self.verilog_module = VerilogModule(name, filename=modulefile, constfile=constfile)
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
        self._get_xwidth_from_consts()
        self.phy = BBoxPHY(self.verilog_module, techfile, spec_dict=self.specs)
        self.phy.place_pins()
        self.lef_builder = BBoxLEFBuilder(self.phy, indent_char_width=2)
        self.gds_builder = GDSDesign(self.phy, layermap_file=layermapfile)
        self.gds_builder.add_polygons()
        self.lib_builder = LIBBuilder(self.phy, corners=cornerfile)

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
        if path:
            filepath = path
        else:
            filepath = self.lef_file_path / (self.name + '.lef')
        self.lef_builder.write_lef(filename=filepath)

    def build_gds(self, path=None):
        if path:
            filepath = path
        else:
            filepath = self.gds_file_path / (self.name + '.gds')
        self.gds_builder.write_gdsfile(filename=filepath)

    def build_lib(self, path=None):
        if path:
            filepath = path
        else:
            filepath = self.lib_file_path / (self.name + '.lib')
        self.lib_builder.write_lib(filepath)

    def build_all(self, lef_path=None, gds_path=None, lib_path=None):
        self.build_lef(path=lef_path)
        self.build_gds(path=gds_path)
        self.build_lib(path=lib_path)

    def _get_xwidth_from_consts(self):
        word_length = self.verilog_module.params['wordLength']
        xwidth = self.per_word_bit_xwidth * int(word_length)
        self.specs['x_width'] = xwidth



class ASAP7SRAMs:
    """This class is a container for all the ASAP7 SRAM black box views2."""

    def __init__(self, behav_file, project_dir, hammer_dir, listfile=None):

        self.project_dir = project_dir
        self.layermapfile = project_dir / 'resources/asap7_TechLib.layermap'
        self.techfile = hammer_dir / 'src/hammer-vlsi/technology/asap7/asap7.tech.json'
        self.cornerfile = project_dir / 'resources/asap7_lib_corners.json'

        self.sramlist = SRAMList(behav_file, listfile)
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
        for line in line_list:
            if re.search("//", line):   # Kill single line comment
                continue
            elif re.match("/\*[\w\W]+\*/", line):   # Kill single line comment defined with /* */
                continue
            elif re.search("/\*", line):    # Get and kill multiline comment beginning
                multiline_comment = True
                continue
            elif multiline_comment and not re.search("\*/", line):  # Still in multiline comment
                continue
            elif re.search("\*/", line):    # Check for end of multiline comment
                multiline_comment = False
                continue
            elif re.match("(?![\s\S])", line):  # Check for empty line
                continue
            else:
                new_line_list.append(line)
        return new_line_list

    def _find_module(self, top):
        for line in self.line_list:
            if top in line.split():
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
        idx = top_line - 1
        line = self.line_list[idx]
        while line != 'endmodule':
            idx += 1
            line = self.line_list[idx]
            module_block.append(line)
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
                                   self.layermapfile, self.cornerfile, self.project_dir / 'views'))


    def build_all_sram_views(self, sram_obj):
        sram_obj.build_all()

    def add_all_srams(self):
        for sram_name in self.srams_names:
            os.mkdir('tmp')
            self._get_relevant_lines(sram_name)
            os.chdir('tmp')
            self.make_sram_objs(sram_name)
            os.chdir('..')
            shutil.rmtree('tmp')

    def build_all_srams(self):
        for sram_obj in self.srams:
            self.build_all_sram_views(sram_obj)

