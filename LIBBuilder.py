from phyrilog.verilog_pin_extract import VerilogModule
import phyrilog.dotlibber.src.dotlibber as dl
from phyrilog.dotlibber.src.dotlibber import default_library_namer
import json
import pathlib
import os
import numpy as np


class Characterizer:

    def characterizer(self, arc_type, timing_type, pin, related_pin, corner, params):
        pass

class LIBBuilder:
    """Builds a LIB view using John Wright's dotlibber"""
    def __init__(self, phy_obj, corners, specs={'all_pins':{},
                                                'output_pins': {}}, characterizer=None, options=None):
        if isinstance(corners, dict):
            self.corners = corners
        elif isinstance(corners, str):
            title, extension = corners.split('.')
            if extension == 'json':
                with open(corners) as json_corners:
                    self.corners = json.load(json_corners)['corners']
            else:
                raise FileNotFoundError(f"Unrecognized corner file {corners}.")
        elif isinstance(corners, pathlib.Path):
            if corners.suffix == '.json':
                with open(corners) as json_corners:
                    self.corners = json.load(json_corners)['corners']
            else:
                raise FileNotFoundError(f"Unrecognized corner file {corners.name}")
        else:
            raise ValueError("Please supply a valid corner file.")
        if characterizer:
            self.characterizer = characterizer.characterizer
        else:
            self.characterizer = dl.default_characterizer

        self.phy_obj = phy_obj
        self.revision = 0

        self.specs = specs

        self.get_pin_attr_from_corner_info()
        self.lib_attr_dict = self.get_lib_attr_dict()
        self.dl_library = dl.Library(self.lib_attr_dict, self.corners, characterizer=self.characterizer, options=options)

    def get_lib_attr_dict(self):
        obj_name = self.phy_obj.name
        lib_attr_dict = {'name': obj_name,
                        'revision': 0,
                         'cells': [{'name': obj_name,
                                    'pins': [],
                                    'pg_pins': []}],
                         }
        for pin_name, pin_dict in self.phy_obj.verilog_pin_dict.items():
            pin_dict.update(self.specs['all_pins'])
            pin_dict.update(self.specs.get(pin_name, {}))
            if pin_dict['direction'] == 'output':
                pin_dict.update(self.specs['output_pins'])
            if 'related_power_pin' not in pin_dict.keys():
                pin_dict['related_power_pin'] = pin_dict.pop('power_pin')
            if 'related_ground_pin' not in pin_dict.keys():
                pin_dict['related_ground_pin'] = pin_dict.pop('ground_pin')
            lib_attr_dict['cells'][0]['pins'].append(pin_dict)
        pg_pins = [{'name': self.phy_obj.verilog_pg_pin_dict['power_pin'],
                    'pg_type': 'primary_power'},
                   {'name': self.phy_obj.verilog_pg_pin_dict['ground_pin'],
                    'pg_type': 'primary_ground'},
                   ]
        lib_attr_dict['cells'][0]['pg_pins'] = pg_pins
        return lib_attr_dict

    def get_pin_attr_from_corner_info(self):
        avg_capacitance = np.mean(self.corners[0]['delay_template']['total_output_net_capacitance'])
        max_capacitance = max(self.corners[0]['delay_template']['total_output_net_capacitance'])
        max_xsition = max(self.corners[0]['delay_template']['input_net_transition'])
        if not self.specs['all_pins'].get('capacitance', None):
            self.specs['all_pins']['capacitance'] = float(avg_capacitance)
        if not self.specs['output_pins'].get('max_capacitance', None):
            self.specs['output_pins']['max_capacitance'] = float(max_capacitance)
        if not self.specs['all_pins'].get('max_transition', None):
            self.specs['all_pins']['max_transition'] = float(max_xsition)

    def write_lib(self, dest_dir=None, lib_namer=None):
        if lib_namer:
            self.dl_library.library_namer = lib_namer

        def file_namer(lib, corner):
                return default_library_namer(lib, corner) + ".lib"

        if dest_dir:
            self.dl_library.write_all(file_namer=file_namer,file_dir=dest_dir)
        else:
            self.dl_library.write_all()
