from verilog_pin_extract import VerilogModule
from verilog2phy import *
from utilities import r_update
import enum

pin_placement_algorithm = ['casual', 'strict']
pin_spacing_options = ['min_pitch', 'distributed', 'center_span']
pg_pin_placement_options = ['small_pins', 'straps', 'interlaced']

pin_specs = {'pins': {'h_layer': "M2",
                      'v_layer': "M3",
                      'pin_length': 1
                      },
             'pg_pins': {'h_layer': "M2",
                         'v_layer': "M3",
                         'pwr_pin': {'layer': 'M3',
                                     'center': None,
                                     'side': 'top'},
                         'gnd_pin': {'layer': 'M3',
                                     'center': None,
                                     'side': 'top'}}
             }

class PinPlacer:
    """Pin placement engine"""

    def __init__(self, pins_dict, pg_pins_dict, techfile, pin_specs=dict()):
        self.pins_dict = pins_dict
        self.pg_pins_dict = pg_pins_dict
        self.defaults = {'strictness': 'casual',
                         'input_side': 'left',
                         'output_side': 'right',
                         'spacing': {'common': 'min_pitch'},
                         'pin_spacing': 'min_pitch',
                         'pg_pin_placement': 'small_pins',
                         'design_boundary': (10,10),
                         'internal_box': [1, 1, 9, 9]
                         }
        self.specs = r_update(self.defaults, pin_specs)
        self._extract_techfile(techfile)

    def _extract_techfile(self, techfile):
        techfile = str(techfile) if not isinstance(techfile, str) else techfile
        if isinstance(techfile, str):
            filetype = techfile.split('.')[-1].lower()  # This normally expects a HAMMER tech.json
        else:
            filetype = techfile.suffix.split('.')[-1].lower()
        if filetype == 'json':
            self._extract_tech_json_info(techfile)
        elif filetype == 'yaml' or filetype == 'yml':
            raise NotImplementedError
        else:
            raise ValueError(f"Unrecognized File Type .{filetype}")

    def _extract_tech_json_info(self, techfile):
        with open(techfile) as file:
            self.tech_dict = json.load(file)
        stackups = self.tech_dict['stackups'][0]['metals']
        self.metals = {}
        for layer in stackups:
            self.metals[layer['name']] = layer
        self.h_pin_width = self.metals[self.specs['pins']['h_layer']]['min_width']
        self.v_pin_width = self.metals[self.specs['pins']['v_layer']]['min_width']
        self.h_pin_pitch = self.metals[self.specs['pins']['h_layer']]['pitch']
        self.v_pin_pitch = self.metals[self.specs['pins']['v_layer']]['pitch']

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

    def _autodefine_boundaries(self):
        min_h_pins = round(max(len(self.pin_sides_dict['left']), len(self.pin_sides_dict['right'])), 3)
        min_v_pins = round(max(len(self.pin_sides_dict['top']), len(self.pin_sides_dict['bottom'])), 3)
        min_y_dim = round(max(sum([pin.y_width for pin in self.pin_sides_dict['left']]),
                        sum([pin.y_width for pin in self.pin_sides_dict['right']])) + ((min_h_pins - 1) * self.h_pin_pitch), 3)
        min_x_dim = round(max(sum([pin.x_width for pin in self.pin_sides_dict['top']]),
                        sum([pin.x_width for pin in self.pin_sides_dict['bottom']])) + ((min_v_pins - 1) * self.v_pin_pitch), 3)
        max_l_pin_length = max(pin.y_width for pin in self.pin_sides_dict['bottom'])
        max_b_pin_length = max(pin.y_width for pin in self.pin_sides_dict['left'])
        max_r_pin_length = max(pin.y_width for pin in self.pin_sides_dict['right'])
        max_t_pin_length = max(pin.y_width for pin in self.pin_sides_dict['top'])
        self.specs['internal_box'] = [max_l_pin_length, max_b_pin_length, min_x_dim, min_y_dim]
        self.specs['design_boundary'] = (min_x_dim + max_l_pin_length + max_r_pin_length, max_t_pin_length)

    def _place_defined_pins(self):
        self.placed_pin_sides_dict = {'left': [],
                               'right': [],
                               'top': [],
                               'bottom': []}
        pin_specs = self.specs['pins']
        for side_name, side in self.pin_sides_dict.items():
            for pin in side:
                if pin.name in pin_specs.keys():
                    x_pos = pin_specs[pin.name].get('x_pos', None)
                    y_pos = pin_specs[pin.name].get('y_pos', None)
                    center = pin_specs[pin.name].get('center', None)
                    if any([x_pos, y_pos, center]): # I'm going to assume that only center is given for now
                        #TODO: Add support for y and x corner definitions
                        if side_name in ['left', 'right']:
                            layer = pin_specs['h_layer']
                            layer = pin_specs[pin.name].get('layer', layer)
                            x_width = round(pin_specs[pin.name].get('x_width', pin_specs['pin_length']), 3)
                            y_width = round(pin_specs[pin.name].get('y_width',self.h_pin_width), 3)
                            left_x = 0 if side_name == 'left' else round(self.specs['design_boundary'][0] -  x_width, 3)
                            right_x = x_width if side_name == 'left' else round(self.specs['design_boundary'][0], 3)
                            top_y = round(center + y_width / 2, 3)
                            bot_y = round(center - y_width / 2, 3)
                        else:
                            layer = pin_specs['h_layer']
                            layer = pin_specs[pin.name].get('layer', layer)
                            x_width = round(pin_specs[pin.name].get('x_width', pin_specs['pin_length']), 3)
                            y_width = round(pin_specs[pin.name].get('y_width',self.h_pin_width), 3)
                            left_x = round(center - x_width / 2, 3)
                            right_x = round(center + x_width / 2, 3)
                            bot_y = 0 if side_name == 'bottom' else round(self.specs['design_boundary'][1] -  y_width, 3)
                            top_y = y_width if side_name == 'bottom' else round(self.specs['design_boundary'][1], 3)
                        self.placed_pin_sides_dict[side_name].append((pin, [left_x, bot_y, right_x, top_y]))

    def _subpartition_sides(self):
        bounds = {'left': (self.specs['internal_box'][1], self.specs['internal_box'][3]),
                  'right': (self.specs['internal_box'][1], self.specs['internal_box'][3]),
                  'top':(self.specs['internal_box'][0], self.specs['internal_box'][2]),
                  'bottom': (self.specs['internal_box'][0], self.specs['internal_box'][2])}



