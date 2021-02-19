from verilog_pin_extract import VerilogModule
from verilog2phy import *
from utilities import *
import numpy as np
import enum

pin_placement_algorithm = ['casual', 'strict']
internal_sizing_strictness = ['flexible', 'strict']
pin_spacing_options = ['min_pitch', 'distributed']
pg_pin_placement_options = ['small_pins', 'straps', 'interlaced']

pin_specs = {'pins': {'h_layer': "M2",
                      'v_layer': "M3",
                      'pin_length': 1
                      },
             'pg_pins': {'h_layer': "M2",
                         'v_layer': "M3",
                         'power_pin': {'layer': 'M3',
                                       'center': None,
                                       'side': 'top'},
                         'ground_pin': {'layer': 'M3',
                                        'center': None,
                                        'side': 'top'}}
             }


class PinPlacer:
    """Pin Placement Engine.

    Parameters
    ----------
    pins_dict : dict
        Dictionary of pins from VerilogModule
    pg_pins_dict : dict
        Dictionary of pg_pins from VerilogModule
    techfile : Path, str
        Path to HAMMER tech.json
    pin_specs : dict
        Dictionary of specifications relevant to pin placement and shape
    options_dict : dict
        Dictionary of options for the pin placer.

    Attributes
    ----------
    pins_dict : dict
        Dictionary of pin dictionaries.
    pg_pins_dict : dict
        Dictionary of pg pin dictionaries.
    defaults : dict
        Default settings for the pin placer.
    specs : Specification
        Specification object containing all specifications and options.
    pins : list
        Flat list of all pin objects.
    autodefined : bool
        Flag indicating if black box boundaries were automatically defined
    pg_pins : dict
        Dictionary of pg pin objects.
    dist_pin_spacing : dict
        Dictionary of per-side distributed pin spacing. This is currently
        not used.
    pin_sides_dict : dict
        Dictionary of pin objects belonging to each side. This dictionary
        is keyed by the name of the side, with corresponding value of a
        list of pin objects beloning to that side.
    placed_pin_sides_dict : dict
        Dictionary of pin objects belonging to each side that have their
        locations defined. This list is populated either by predefining
        the pin locations in the pin_specs, or when a free pin is placed
        by the pin placer.
    sig_figs : int
        Decimal significant figure precision of all coordinates.
    """

    def __init__(self, pins_dict, pg_pins_dict, techfile, pin_specs=dict(), options_dict=dict()):
        self.pins_dict = pins_dict
        self.pg_pins_dict = pg_pins_dict
        self.defaults = {'origin': [0, 0],
                         'units': 1e-6,
                         'precision': 1e-9,
                         'input_side': 'left',
                         'output_side': 'right',
                         'pin_margin': False,
                         'internal_strictness': 'flexible',
                         'pin_strictness': 'strict',
                         'wrap_direction': 'clockwise',
                         'port_sides': {
                             'input': 'left',
                             'output': 'right',
                         },
                         'pg_pin_sides': {
                             'power_pin': 'top',
                             'ground_pin': 'top'
                         },
                         'spacing': {'common': 'min_pitch'},
                         'pin_spacing': 'min_pitch',
                         'design_boundary': (10, 10),
                         'internal_box': [1, 1, 9, 9],
                         'pins': {'h_layer': "M2",
                                  'v_layer': "M3",
                                  'pin_length': 1},
                         'pg_pins': {'h_layer': 'M4',
                                     'v_layer': 'M5',
                                     'pg_pin_placement': 'small_pins'}
                         }
        self.specs = r_update(self.defaults, pin_specs)
        self.specs = r_update(self.specs, options_dict)
        self._extract_techfile(techfile)
        self.pins = []
        self.sig_figs = int(-(np.log10(self.specs['units']) - np.log10(self.specs['precision'])))
        self.autodefined = False
        self.pg_pins = {}
        self.dist_pin_spacing = {'left': 0,
                                 'bottom': 0,
                                 'right': 0,
                                 'top': 0}
        self.pin_sides_dict = {'left': [],
                               'right': [],
                               'top': [],
                               'bottom': []}
        self.placed_pin_sides_dict = {'left': [],
                                      'right': [],
                                      'top': [],
                                      'bottom': []}
        self._define_pg_pin_dicts()
        self._sort_pins_by_side()

    def _define_pg_pin_dicts(self):
        """
        Defines PG pin dictionaries.
        Returns
        -------

        """
        pg_pin_dicts = {}
        for purpose, pin in self.pg_pins_dict.items():
            pg_pin_dicts[purpose] = {'name': pin,
                                     'direction': 'inout',
                                     'is_analog': False}
        self.power_pin = pg_pin_dicts['power_pin']
        self.ground_pin = pg_pin_dicts['ground_pin']

    def _extract_techfile(self, techfile):
        """
        Dispatcher to extract routing information from a techfile.
        Currently only supports HAMMER tech.json.
        Parameters
        ----------
        techfile : Path
            Path to techfile/

        Returns
        -------

        """
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
        """
        Extracts routing information from HAMMER tech.json to dictionaries.
        Parameters
        ----------
        techfile : Path
            Path to techfile.

        Returns
        -------

        """
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
        """
        Sorts pins defined in pins_dict by side based on sorting rules
        defined in pin_specs.
        Returns
        -------

        """
        # TODO: Make the pin sorting algorithm configurable
        pin_specs = self.specs['pins']
        for pin in self.pins_dict.values():
            side = self.specs['port_sides'][pin['direction']]
            if pin['name'] in pin_specs.keys():
                side = pin_specs[pin['name']].get('side', side)
            orientation = get_orientation(side)
            x_width = pin_specs['pin_length'] if orientation == 'horizontal' else self.metals[pin_specs['v_layer']][
                'min_width']
            y_width = pin_specs['pin_length'] if orientation == 'vertical' else self.metals[pin_specs['h_layer']][
                'min_width']
            layer = self.specs['pins']['h_layer'] if orientation == 'horizontal' else self.specs['pins']['v_layer']
            center = None
            if pin['name'] in self.specs['pins'].keys():
                layer = self.specs['pins'][pin['name']].get('layer', layer)
                center = self.specs['pins'][pin['name']].get('center', None)
            if 'is_bus' in pin.keys():
                for bus_idx in range(pin['bus_max'] + 1):
                    pin_obj = PHYPortPin(pin, layer, side, x_width, y_width, bus_idx=bus_idx)
                    pin_obj.name = pin['name'] + '[' + str(bus_idx) + ']'
                    self.pin_sides_dict[side].append(pin_obj)
                    self.pins.append(pin_obj)
            else:
                pin_obj = PHYPortPin(pin, layer, side, x_width, y_width, center=center)
                self.pin_sides_dict[side].append(pin_obj)
                self.pins.append(pin_obj)
        if self.specs['pg_pins']['pg_pin_placement'] == pg_pin_placement_options[0]:
            for purpose, pg_pin in self.pg_pins_dict.items():
                pg_pin_dict = {'name': pg_pin,
                               'direction': 'inout',
                               'is_analog': False,
                               'purpose': purpose}
                side = self.specs['pg_pin_sides'][purpose]
                orientation = get_orientation(side)
                x_width = pin_specs['pin_length'] if orientation == 'horizontal' else self.metals[pin_specs['v_layer']][
                    'min_width']
                y_width = pin_specs['pin_length'] if orientation == 'vertical' else self.metals[pin_specs['h_layer']][
                    'min_width']
                layer = self.specs['pg_pins']['h_layer'] if orientation == 'horizontal' else self.specs['pg_pins'][
                    'v_layer']
                if purpose in self.specs['pg_pins'].keys():
                    layer = self.specs['pg_pins'][purpose].get('layer', layer)
                    center = self.specs['pg_pins'][purpose].get('center', None)
                if 'multiplier' in self.specs['pg_pins'].keys():
                    for idx in range(pg_pin['multiplier'] + 1):
                        spacing = 2 * self.metals[layer]['min_width'] + 2 * self.metals[layer]['pitch']
                        new_cent = center + round(idx * spacing, self.sig_figs)
                        pin_obj = PHYPortPin(pg_pin_dict, layer, side, x_width, y_width, center=new_cent)
                        self.pin_sides_dict[side].append(pin_obj)
                        # self.pins.append(pin_obj)
                        self.pg_pins.append(pin_obj)
                else:
                    pin_obj = PHYPortPin(pg_pin_dict, layer, side, x_width, y_width, center=center)
                    self.pin_sides_dict[side].append(pin_obj)
                    # self.pins.append(pin_obj)
                    if purpose == 'power':
                        self.pg_pins['pwr'] = pin_obj
                    else:
                        self.pg_pins['gnd'] = pin_obj
        self.h_pin_spacing = self.h_pin_pitch - self.h_pin_width
        self.v_pin_spacing = self.v_pin_pitch - self.v_pin_width
        self.min_h_pins = round(max(len(self.pin_sides_dict['left']), len(self.pin_sides_dict['right'])), self.sig_figs)
        self.min_v_pins = round(max(len(self.pin_sides_dict['top']), len(self.pin_sides_dict['bottom'])), self.sig_figs)
        self.min_y_dim = round(max(sum([pin.y_width for pin in self.pin_sides_dict['left']]) +
                                   (self.min_h_pins - 1) * self.h_pin_spacing,
                                   sum([pin.y_width for pin in self.pin_sides_dict['right']]) + (
                                           (self.min_h_pins - 1) * self.h_pin_spacing)), self.sig_figs)
        self.min_x_dim = round(max(sum([pin.x_width for pin in self.pin_sides_dict['top']]) +
                                   (self.min_v_pins - 1) * (self.v_pin_spacing),
                                   sum([pin.x_width for pin in self.pin_sides_dict['bottom']]) + (
                                           (self.min_v_pins - 1) * self.v_pin_pitch)), self.sig_figs)
        self.max_b_pin_length = max_none([pin.y_width for pin in self.pin_sides_dict['bottom']])
        self.max_l_pin_length = max_none([pin.x_width for pin in self.pin_sides_dict['left']])
        self.max_r_pin_length = max_none([pin.x_width for pin in self.pin_sides_dict['right']])
        self.max_t_pin_length = max_none([pin.y_width for pin in self.pin_sides_dict['top']])

    def autodefine_boundaries(self):
        """
        Automatically define black box boundaries from pin lists. This
        method guarantees the black box will be able to fit all pins but
        may not return realistic dimensions. This method takes aspect ratio
        specification into account.
        Returns
        -------

        """
        pin_specs = self.specs['pins']
        self.autodefined = True
        self.specs['internal_box'] = [round(self.max_l_pin_length, self.sig_figs),
                                      round(self.max_b_pin_length, self.sig_figs),
                                      round(self.min_x_dim + self.max_l_pin_length, self.sig_figs),
                                      round(self.min_y_dim + self.max_b_pin_length, self.sig_figs)]
        self.specs['design_boundary'] = [
            self.min_x_dim + self.max_l_pin_length + self.max_r_pin_length,
            self.min_y_dim + self.max_t_pin_length + self.max_b_pin_length]

        if self.specs.get('aspect_ratio', None):
            dom_dim_idx = self.specs['design_boundary'].index(max(self.specs['design_boundary']))
            sub_dim_idx = self.specs['design_boundary'].index(min(self.specs['design_boundary']))
            sub_dim = round(self.specs['design_boundary'][dom_dim_idx] / self.specs['aspect_ratio'][dom_dim_idx] *
                            self.specs['aspect_ratio'][sub_dim_idx], self.sig_figs)
            self.specs['design_boundary'][sub_dim_idx] = round(sub_dim, self.sig_figs)
            box_sides = [self.specs['internal_box'][2] - self.specs['internal_box'][0],
                         self.specs['internal_box'][3] - self.specs['internal_box'][1]]
            dom_dim_idx = box_sides.index(max(box_sides))
            sub_dim_idx = box_sides.index(min(box_sides))
            sub_dim = round(box_sides[dom_dim_idx] / self.specs['aspect_ratio'][dom_dim_idx] *
                            self.specs['aspect_ratio'][sub_dim_idx], self.sig_figs)
            box_sides[sub_dim_idx] = sub_dim
            self.specs['internal_box'][2 + sub_dim_idx] = round(self.specs['internal_box'][0 + sub_dim_idx] + sub_dim,
                                                                self.sig_figs)
        if self.specs['pin_margin']:
            margins = np.asarray([0, 0, self.v_pin_pitch, self.h_pin_pitch])
            self.specs['design_boundary'] = [
                round(self.min_x_dim + self.max_l_pin_length + self.max_r_pin_length + 2 * self.v_pin_pitch, self.sig_figs),
                round(self.min_y_dim + self.max_t_pin_length + self.max_b_pin_length + 2 * self.h_pin_pitch, self.sig_figs)]
            inner_box = np.asarray(self.specs['internal_box']) + margins
            self.specs['internal_box'] = inner_box.tolist()
        self.specs['design_boundary'] = [self.specs['internal_box'][2] + self.max_r_pin_length,
                                         self.specs['internal_box'][3] + self.max_t_pin_length]
        bound_corner = np.asarray(self.specs['origin']) + np.asarray(self.specs['design_boundary'])
        self.specs['design_boundary'] = bound_corner.tolist()
        self.specs['bound_box'] = self.specs['origin'] + bound_corner.tolist()

    def _place_defined_pins(self):
        """
        Place all pins with pre-defined locations. Reads the pin_specs dict
        for pins with defined locations and creates PHYPortPin objects and
        corresponding Rectangles and appends to placed_pin_sides_dict.
        Returns
        -------

        """
        pin_specs = self.specs['pins']
        for side_name, side in self.pin_sides_dict.items():
            for pin in side:
                if pin.name in pin_specs.keys():
                    x_pos = pin_specs[pin.name].get('x_pos', None)
                    y_pos = pin_specs[pin.name].get('y_pos', None)
                    center = pin_specs[pin.name].get('center', None)
                    if any([x_pos, y_pos, center]):  # I'm going to assume that only center is given for now
                        # TODO: Add support for y and x corner definitions
                        if side_name in ['left', 'right']:
                            layer = pin_specs['h_layer']
                            layer = pin_specs[pin.name].get('layer', layer)
                            x_width = round(pin_specs[pin.name].get('x_width', pin_specs['pin_length']), self.sig_figs)
                            y_width = round(pin_specs[pin.name].get('y_width', self.h_pin_width), self.sig_figs)
                            left_x = 0 if side_name == 'left' else round(self.specs['design_boundary'][0] - x_width, self.sig_figs)
                            right_x = x_width if side_name == 'left' else round(self.specs['design_boundary'][0], self.sig_figs)
                            top_y = round(center + y_width / 2, self.sig_figs)
                            bot_y = round(center - y_width / 2, self.sig_figs)
                        else:
                            layer = pin_specs['v_layer']
                            layer = pin_specs[pin.name].get('layer', layer)
                            x_width = round(pin_specs[pin.name].get('x_width', pin_specs['pin_length']), self.sig_figs)
                            y_width = round(pin_specs[pin.name].get('y_width', self.h_pin_width), self.sig_figs)
                            left_x = round(center - x_width / 2, self.sig_figs)
                            right_x = round(center + x_width / 2, self.sig_figs)
                            bot_y = 0 if side_name == 'bottom' else round(self.specs['design_boundary'][1] - y_width, self.sig_figs)
                            top_y = y_width if side_name == 'bottom' else round(self.specs['design_boundary'][1], self.sig_figs)
                        pin.add_rect(layer, left_x=left_x, bot_y=bot_y)
                        self.placed_pin_sides_dict[side_name].append(pin)
                        side.pop(side.index(pin))

    def _make_subpartitions(self):
        """
        Coordinate subpartitioning of each side of design.

        The subpartition algorithm allows the pin placer to work with
        pre-determined pin locations by treating each side as an interval
        within which free pins may be placed. Each placed pin creates a
        keepout zone around it, which is represented in the subpartition
        algorithm as a division of an interval into two subintervals with
        the pin keepout in between. This ensures all pin placements
        adhere to design rules.
        Returns
        -------

        """
        self.partitions = {'left': [],
                           'right': [],
                           'top': [],
                           'bottom': []}
        h_pin_margin = round(self.specs.get('pin_margin', False) *
                             self.metals[self.specs['pins']['h_layer']]['pitch'] * 0.5, self.sig_figs)
        v_pin_margin = round(self.specs.get('pin_margin', False) *
                             self.metals[self.specs['pins']['v_layer']]['pitch'] * 0.5, self.sig_figs)
        bounds = {'left': [self.specs['internal_box'][1] + h_pin_margin, self.specs['internal_box'][3] - h_pin_margin],
                  'right': [self.specs['internal_box'][1] + h_pin_margin, self.specs['internal_box'][3] - h_pin_margin],
                  'top': [self.specs['internal_box'][0] + v_pin_margin, self.specs['internal_box'][2] - v_pin_margin],
                  'bottom': [self.specs['internal_box'][0] + v_pin_margin,
                             self.specs['internal_box'][2] - v_pin_margin]}
        for side in self.partitions.keys():
            self.partitions[side] += self._subpartition_side([bounds[side]], self.placed_pin_sides_dict[side])
        for side, pin_space in self.dist_pin_spacing.items():
            pin_space = 0
            for partition in self.partitions[side]:
                pin_space += round(partition[1] - partition[0], self.sig_figs)
            if self.pin_sides_dict[side]:
                self.dist_pin_spacing[side] = round(pin_space / len(self.pin_sides_dict[side]), self.sig_figs)

    def _subpartition_interval(self, bounds, rect):
        """Subpartitions a given interval with the given placed pin.
        Parameters
        ---------
        bounds: list[float, float]
            Lower and upper bound of interval, respectively
        rect: Rectangle object
            Rectangle object occupying dividing space

        Returns
        -------
        partitions : list
            List of new partitions.
        """
        center = rect.center
        layer = rect.layer
        pin_dimensions = rect.coords
        if btwn(center, bounds):
            pitch = self.metals[layer]['pitch']
            direction = self.metals[layer]['direction']
            if direction == 'horizontal':
                lower_interval = [round(bounds[0], self.sig_figs), round(pin_dimensions[3] - pitch, self.sig_figs)]
                upper_interval = [round(pin_dimensions[1] + pitch, self.sig_figs), round(bounds[1], self.sig_figs)]
            else:
                lower_interval = [round(bounds[0], self.sig_figs), round(pin_dimensions[2] - pitch, self.sig_figs)]
                upper_interval = [round(pin_dimensions[0] + pitch, self.sig_figs), round(bounds[1], self.sig_figs)]
            partitions = [lower_interval, upper_interval]
        else:
            partitions = [bounds]
        return partitions

    def _subpartition_side(self, side_bounds, placed_pins):
        """
        Iterates subpartitioning method over all pins on a side.
        Parameters
        ----------
        side_bounds : list[lower_bound, upper_bound]
            List of bounding coordinates of the side.
        placed_pins : list[PHYPortPin]
            List of placed pin objects.

        Returns
        -------
        partitions : list
            List of new partitions.
        """
        partitions = side_bounds
        for pin_obj in placed_pins:
            for rect in pin_obj.rects.values():
                center = rect.center
                for partition in partitions:
                    if btwn(center, partition):
                        new_part = self._subpartition_interval(partition, rect)
                        partitions = replace(partitions, new_part, partitions.index(partition))
        return partitions

    def place_interlaced_pg_pins(self, layer, interlace_interval, side_bounds):
        """
        Places PG pins using the interlacing placement scheme. Interlacing
        means the PG straps are placed between signal pins at a regular
        interval of pins.
        Parameters
        ----------
        layer : str
            Layer on which to draw pg pin objects.
        interlace_interval : int
            Number of pins between each PG strap.
        side_bounds : list[lower_bound, upper_bound]
            Bounding coordinates of the side to place pg straps on.

        Returns
        -------

        """
        pg_pin_specs = self.specs['pg_pins']
        width = self.metals[layer]['min_width']
        pitch = self.metals[layer]['pitch']
        horizontal = self.metals[layer]['direction'] == 'horizontal'
        sides = ['left', 'right'] if horizontal else ['top', 'bottom']
        pin_window = round(pitch, self.sig_figs)
        side_length = side_bounds[1] - side_bounds[0]
        a = 2 * pg_pin_specs.get('strap_width', width)
        b = pg_pin_specs.get('strap_spacing', pitch)
        strap_width = pg_pin_specs.get('strap_width', width)
        strap_spacing = pg_pin_specs.get('strap_spacing', round(pitch - strap_width / 2, self.sig_figs))
        interlace_size = round(2 * strap_width + strap_spacing, self.sig_figs)
        interlace_chunk = round(pin_window * interlace_interval + interlace_size + (pitch - width / 2), self.sig_figs)
        if horizontal:
            n_interlaces = int(np.floor(self.min_h_pins / interlace_interval))
        else:
            n_interlaces = int(np.floor(self.min_v_pins / interlace_interval))
        if self.specs['pin_spacing'] == 'distributed':
            n_pins = max([len(self.pin_sides_dict[sides[0]]), len(self.pin_sides_dict[sides[1]])])
            interlace_region = n_interlaces * interlace_size
            pin_region = (side_length - interlace_region) / n_pins
            if pin_region > (pitch):
                for side in sides:
                    if horizontal:
                        total_pin_width = sum(pin.y_width for pin in self.pin_sides_dict[side])
                    else:
                        total_pin_width = sum(pin.x_width for pin in self.pin_sides_dict[side])
                    self.dist_pin_spacing[side] = round((side_length - total_pin_width) /
                                                        (len(self.pin_sides_dict[side])), self.sig_figs) \
                        if self.pin_sides_dict[side] else pitch
                pin_window = min(self.dist_pin_spacing[sides[0]], self.dist_pin_spacing[sides[1]])
        start = side_bounds[0] + self.specs['pin_margin'] * pitch * 0.5
        vdd_obj1, gnd_obj1, vdd_obj2, gnd_obj2 = self._get_pg_strap_objs(p_layer=layer)
        # self.power_pin = vdd_obj1
        # self.ground_pin = gnd_obj1
        interlace_list = [vdd_obj1, vdd_obj2, gnd_obj1, gnd_obj2]
        self.placed_pin_sides_dict[sides[0]] += [vdd_obj1, gnd_obj1]
        self.placed_pin_sides_dict[sides[1]] += [vdd_obj1, gnd_obj1]
        # for side in sides:
        #     self.placed_pin_sides_dict[side] += interlace_list
        for n in range(n_interlaces):
            vdd_center = round(start + pin_window * interlace_interval + strap_width * 0.5, self.sig_figs)
            start = round(start + pin_window * interlace_interval + interlace_size + (pitch - width) * 0.5, self.sig_figs)
            if self.autodefined:
                self.specs['internal_box'][2 + horizontal] += round(interlace_size + (pitch - width) * 0.5, self.sig_figs)
            if horizontal:
                self.min_y_dim += round(interlace_size + (pitch - width) * 0.5, self.sig_figs)
            else:
                self.min_x_dim += round(interlace_size + (pitch - width) * 0.5, self.sig_figs)
            self.draw_pg_strap(vdd_center, vdd_obj1, gnd_obj1, layer=layer, pair=True)

    def _get_pg_strap_objs(self, p_layer=None, g_layer=None):
        """
        Returns PHYPortPin objects corresponding to PG straps.
        Parameters
        ----------
        p_layer : str, optional
            Layer on which to place power strap. If not defined, checks
            specification dictionary for layer.
        g_layer : str, optional
            Layer on which to place ground strap. If not defined, defaults
            to p_layer.

        Returns
        -------
        vdd_obj1, gnd_obj1, vdd_obj2, gnd_obj2 : PHYPortPin
            PHYPortPin Objects corresponding to the power straps that are
            to be defined. Each come as a pair as the straps extend across
            the entire design, and therefore must be treated as pins on
            both sides (left/right or top/bottom).
        """
        pg_pin_dicts = {}
        pg_pin_specs = self.specs['pg_pins']
        vdd_side = self.specs['pg_pins'].get('side', self.defaults['pg_pin_sides']['power_pin'])
        gnd_side = self.specs['pg_pins'].get('side', self.defaults['pg_pin_sides']['ground_pin'])
        vdd_orientation = get_orientation(vdd_side)
        gnd_orientation = get_orientation(gnd_side)
        vdd_layer = pg_pin_specs['pwr_pin'].get('layer', pg_pin_specs['h_layer'] \
            if vdd_orientation == 'horizontal' else pg_pin_specs['v_layer'])
        gnd_layer = pg_pin_specs['pwr_pin'].get('layer', pg_pin_specs['h_layer'] \
            if gnd_orientation == 'horizontal' else pg_pin_specs['v_layer'])
        if p_layer:
            vdd_layer = p_layer
        if g_layer:
            gnd_layer = g_layer
        elif p_layer:
            gnd_layer = p_layer
        for purpose, pin in self.pg_pins_dict.items():
            pg_pin_dicts[purpose] = {'name': pin,
                                     'direction': 'inout',
                                     'is_analog': False}
        if self.metals[vdd_layer]['direction'] == 'horizontal':
            vdd_xwidth = round(self.specs['design_boundary'][0], self.sig_figs)
            vdd_ywidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), self.sig_figs)
            gnd_xwidth = vdd_xwidth
            gnd_ywidth = vdd_ywidth
        else:
            vdd_ywidth = round(self.specs['design_boundary'][1], self.sig_figs)
            vdd_xwidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), self.sig_figs)
            gnd_xwidth = vdd_xwidth
            gnd_ywidth = vdd_ywidth
        side = ['left', 'right'] if pg_pin_specs['strap_orientation'] == 'horizontal' else ['top', 'bottom']
        vdd_obj1 = PHYPortPin(pg_pin_dicts['power_pin'], vdd_layer, side[0], vdd_xwidth, vdd_ywidth)
        gnd_obj1 = PHYPortPin(pg_pin_dicts['ground_pin'], gnd_layer, side[0], gnd_xwidth, gnd_ywidth)
        vdd_obj2 = PHYPortPin(pg_pin_dicts['power_pin'], vdd_layer, side[1], vdd_xwidth, vdd_ywidth)
        gnd_obj2 = PHYPortPin(pg_pin_dicts['ground_pin'], gnd_layer, side[1], gnd_xwidth, gnd_ywidth)
        self.pg_pins['pwr'] = vdd_obj1
        self.pg_pins['gnd'] = gnd_obj1
        return vdd_obj1, gnd_obj1, vdd_obj2, gnd_obj2

    def draw_pg_strap(self, center, pwr_obj, gnd_obj, layer=None, pair=True):
        """
        Adds Rectangle objects to each pg strap object.
        Parameters
        ----------
        center : float
            Center coordinate of PG strap.
        pwr_obj : PHYPortPin
            PHYPortPin object corresponding to the power strap.
        gnd_obj : PHYPortPin
            PHYPortPin objects corresponding to the ground strap.
        layer : str, optional
            Layer on which to draw PG strap. Defaults to spec dict lookup.
        pair : bool, optional
            P and G straps generated together? Defaults to True.

        Returns
        -------
        pwr_coords, gnd_coords : list
            Coordinates of generated Rectangle objects.
        """
        pg_pin_dicts = {}
        pg_pin_specs = self.specs['pg_pins']
        for purpose, pin in self.pg_pins_dict.items():
            pg_pin_dicts[purpose] = {'name': pin,
                                     'direction': 'inout',
                                     'is_analog': False}
        vdd_layer = layer if layer else pg_pin_specs['pwr_pin']['layer']
        if self.metals[vdd_layer]['direction'] == 'horizontal':
            vdd_xwidth = round(self.specs['design_boundary'][0], self.sig_figs)
            vdd_ywidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), self.sig_figs)
            vdd_pos = round(center - vdd_ywidth / 2, self.sig_figs)
            if pair:
                pitch = self.specs.get('strap_spacing', self.metals[vdd_layer]['pitch'])
                gnd_xwidth = vdd_xwidth
                gnd_ywidth = vdd_ywidth
                gnd_pos = round(vdd_pos + pitch, self.sig_figs)
                gnd_center = round(center + pitch, self.sig_figs)
        else:
            vdd_ywidth = round(self.specs['design_boundary'][1], self.sig_figs)
            vdd_xwidth = round(pg_pin_specs.get('strap_width', self.metals[vdd_layer]['min_width']), self.sig_figs)
            vdd_pos = round(center - vdd_xwidth / 2, self.sig_figs)
            if pair:
                pitch = self.specs.get('strap_spacing', self.metals[vdd_layer]['pitch'])
                gnd_xwidth = vdd_xwidth
                gnd_ywidth = vdd_ywidth
                gnd_pos = round(vdd_pos + pitch, self.sig_figs)
                gnd_center = round(center + pitch, self.sig_figs)
        # if not pwr_obj:
        #     pwr_obj = PHYPortPin(pg_pin_dicts['pwr_pin'], vdd_layer, vdd_xwidth, vdd_ywidth, center=center)
        if not pair:
            gnd_layer = layer if layer else pg_pin_specs['gnd_pin']['layer']
            if self.metals[gnd_layer]['direction'] == 'horizontal':
                gnd_xwidth = round(self.specs['design_boundary'][0], self.sig_figs)
                gnd_ywidth = round(pg_pin_specs.get('strap_width', self.metals[gnd_layer]['min_width']), self.sig_figs)
                gnd_pos = round(center - gnd_ywidth / 2, self.sig_figs)
            else:
                gnd_ywidth = round(self.specs['design_boundary'][1], self.sig_figs)
                gnd_xwidth = round(pg_pin_specs.get('strap_width', self.metals[gnd_layer]['min_width']), self.sig_figs)
                gnd_pos = round(center - gnd_ywidth / 2, self.sig_figs)
        # if not gnd_obj:
        #     gnd_obj = PHYPortPin(pg_pin_dicts['gnd_pin'], gnd_layer, gnd_xwidth, gnd_ywidth, center=center)
        pwr_obj.x_width = vdd_xwidth
        pwr_obj.y_width = vdd_ywidth
        gnd_obj.x_width = gnd_xwidth
        gnd_obj.y_width = gnd_ywidth
        if self.metals[vdd_layer]['direction'] == 'horizontal':
            if vdd_pos + vdd_ywidth > self.specs['internal_box'][3] \
                    or gnd_pos + gnd_ywidth > self.specs['internal_box'][3]:
                return [], []
            pwr_obj.add_rect(vdd_layer, left_x=0, bot_y=vdd_pos)
            gnd_obj.add_rect(vdd_layer, left_x=0, bot_y=gnd_pos)
        else:
            if vdd_pos + vdd_xwidth > self.specs['internal_box'][2] \
                    or gnd_pos + gnd_xwidth > self.specs['internal_box'][2]:
                return pwr_obj.rects[center].coords, gnd_obj.rects[gnd_center].coords
            pwr_obj.add_rect(vdd_layer, left_x=vdd_pos, bot_y=0)
            gnd_obj.add_rect(vdd_layer, left_x=gnd_pos, bot_y=0)
        return pwr_obj.rects[center].coords, gnd_obj.rects[gnd_center].coords

    def place_free_pins(self):
        """
        Place all free placement pins.
        Returns
        -------

        """
        for side, partitions in self.partitions.items():
            pin_list = self.pin_sides_dict[side]
            while len(partitions) > 0:
                interval = partitions.pop(0)
                orientation = get_orientation(side)
                if side == 'left' or side == 'bottom':
                    ref_edge = 0
                elif side == 'right':
                    ref_edge = self.specs['internal_box'][2]
                elif side == 'top':
                    ref_edge = self.specs['internal_box'][3]
                pin_list, placed_pins = self._placement_engine_dispatcher(interval, orientation, ref_edge, pin_list,
                                                                          side)
                self.placed_pin_sides_dict[side] += placed_pins

    def _placement_engine_dispatcher(self, *args):
        """
        Dispatches pin placement to appropriate placement engine.
        Parameters
        ----------
        args : args
            All arguments passed through to pin placement engine.

        Returns
        -------
        return
            Returns result from pin placement engine.
        """
        dispatch_dict = {'min_pitch': self._minimum_pitch_engine,
                         'distributed': self._distributed_place_engine,
                         # 'center-span': self._center_span_engine
                         }
        placement_engine = dispatch_dict[self.specs['pin_spacing']]
        return placement_engine(*args)

    def _minimum_pitch_engine(self, interval, orientation, ref_edge, pin_list, *args):
        """
        Places pins assuming minimum pitch between each pin within given
        interval. Continues placing pins until no more can fit in interval.
        Parameters
        ----------
        interval : list[lower_bound, upper_bound]
            Bounding coordinates of valid interval for placement.
        orientation : ('horiztonal', 'vertical')
            Orientation of pin.
        ref_edge : ('left', 'bottom')
            Edge of design to use as reference coordinate. Only left and
            bottom edges are valid.
        pin_list : List
            List of pins to place.
        args
            Extra arguments.

        Returns
        -------
        pin_list : list
            List of remaining unplaced pins after placement.
        placed_pins : list
            List of placed pins.
        """
        lower = interval[0]
        # upper = interval[0]
        placed_pins = []
        while lower < interval[1] and len(pin_list) > 0:
            pin = pin_list.pop(0)
            layer = pin.layer
            width = pin.y_width if orientation == 'horizontal' else pin.x_width
            pitch = self.metals[layer]['pitch']
            lower_dim = round(lower, self.sig_figs)
            upper_dim = round(lower + width, self.sig_figs)
            if upper_dim > interval[1]:
                return pin_list, placed_pins
            if orientation == 'horizontal':
                pin.add_rect(layer, left_x=ref_edge, bot_y=lower_dim)
            else:
                pin.add_rect(layer, left_x=lower_dim, bot_y=ref_edge)
            lower = round(lower_dim + pitch, self.sig_figs)
            placed_pins.append(pin)
        return pin_list, placed_pins

    def _distributed_place_engine(self, interval, orientation, ref_edge, pin_list, side):
        """
        THIS METHOD IS NOT USED.

        Parameters
        ----------
        interval
        orientation
        ref_edge
        pin_list
        side

        Returns
        -------

        """
        interval_size = interval[1] - interval[0]
        spacing = self.dist_pin_spacing[side]
        if len(pin_list) == 0:
            return [], pin_list
        elif spacing <= self.metals[pin_list[0].layer]['pitch'] - self.metals[pin_list[0].layer]['min_width']:
            return self._minimum_pitch_engine(interval, orientation, ref_edge, pin_list)
        else:
            placed_pins = []
            layer = pin_list[0].layer
            width = pin_list[0].y_width if orientation == 'horizontal' else pin_list[0].x_width
            n_pins = int(np.floor(interval_size / (width + spacing)))
            leftover = round(interval_size - n_pins * (width + spacing), self.sig_figs)
            start = round(leftover / 2 + interval[0], self.sig_figs)
            for n in range(n_pins):
                pin = pin_list.pop(0)
                if orientation == 'horizontal':
                    pin.add_rect(layer, left_x=ref_edge, bot_y=start)
                else:
                    pin.add_rect(layer, left_x=start, bot_y=ref_edge)
                start += round(width + spacing, self.sig_figs)
                placed_pins.append(pin)
            return pin_list, placed_pins

    def place_pins(self):
        """
        Master method to perform all the steps in pin placement.
        Returns
        -------
        failed : int
            Exit code for the pin placement process. 1 if failed to place
            all pins, 0 if successful.
        """
        self._place_defined_pins()
        if self.specs['pg_pins']['pg_pin_placement'] == 'interlaced':
            try:
                interval = self.specs['pg_pins']['interlace_interval']
            except KeyError:
                raise KeyError("Interlace Interval not defined in options dict.")
            try:
                orientation = self.specs['pg_pins']['strap_orientation'] == 'horizontal'
            except KeyError:
                raise KeyError("Strap Orientation not defined in options dict.")
            layer = self.power_pin.get('layer',
                                       self.specs['pg_pins']['h_layer'] if orientation else
                                       self.specs['pg_pins']['v_layer'])
            bounds = [self.specs['internal_box'][0 + orientation],
                      self.specs['internal_box'][2 + orientation]]
            self.place_interlaced_pg_pins(layer, interval, bounds)
        self._make_subpartitions()
        self.place_free_pins()
        failed = False
        for side, pin_list in self.pin_sides_dict.items():
            if pin_list:
                failed = True
                print(f"WARNING: Not all pins on the {side} side were able to be placed!")
                print(f"The following pins on the {side} side were not placed:")
                for pin in pin_list:
                    print(f"\t{pin.name}")
        return int(failed)

    def _clean_pin_lists(self):
        """
        Removes "ghost" pins. During pg strapping, non-real pins are
        created to allow for proper side partitioning. These pins must be
        removed prior to generation of physical views.
        Returns
        -------
        """
        clean_list = []
        for pin_obj in self.pg_pins.values():
            if pin_obj.rects:
                clean_list.append(pin_obj)
        self.pg_pins = clean_list
        clean_list = []
        for pin_obj in self.pins:
            if pin_obj.rects:
                clean_list.append(pin_obj)
            else:
                print(f"WARNING: Pin {pin_obj.name} has no associated rectangles and is being removed!")
        self.pins = clean_list
