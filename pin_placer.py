from verilog_pin_extract import VerilogModule
from verilog2phy import *
from utilities import r_update
import enum

pin_placement_algorithm = ['casual', 'strict']
pin_spacing_options = ['min_pitch', 'distributed', 'center_span']
pg_pin_placement_options = ['small_pins', 'straps', 'interlaced']

class PinPlacer:
    """Pin placement engine"""
    def __init__(self, pins_dict, pg_pins_dict, techfile, pin_specs=dict()):
        self.pins_dict = pins_dict
        self.pg_pins_dict = pg_pins_dict
        self.defaults = {'strictness': 'casual',
                         'input_side': 'left',
                         'output_side': 'right',
                         'spacing':{'common':'min_pitch'},
                         'pin_spacing': 'min_pitch',
                         'pg_pin_placement': 'small_pins'
                         }
        self.specs = r_update(self.defaults, pin_specs)

    def _extract_techfile(self, techfile):
        techfile = str(techfile) if not isinstance(techfile, str) else techfile
        if isinstance(techfile, str):
            filetype = techfile.split('.')[-1].lower()  # This normally expects a HAMMER tech.json
        else:
            filetype = techfile.suffix.split('.').lower()
        if filetype == 'json':
            self._extract_tech_json_info(techfile)
        elif filetype == 'yaml' or filetype == 'yml':
            raise NotImplementedError
        else:
            raise ValueError(f"Unrecognized File Type .{filetype}")

    def _sort_pins_by_side(self):
        self.pin_sides_dict = {'left': [],
                               'right': [],
                               'top': [],
                               'bottom': []}
        for pin in self.pins_dict.values():
            self.pin_sides_dict[pin.side].append(pin)
        if self.specs['pg_pin_placement'] == pg_pin_placement_options[0]:
            for pg_pin in self.pg_pins_dict.values():
                self.pin_sides_dict[pg_pin.side].append(pg_pin)


