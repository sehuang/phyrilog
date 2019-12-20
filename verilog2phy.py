import json
import numpy as np
from specification import Specification
from utilities import *

class Rectangle:
    """
    Representation of a physical rectangle object.

    Parameters
    ----------
    layer : str
        Layout layer the rectangle exists on.
    left_x : float
        X-coordinate of left edge.
    bot_y : float
        Y-coordinate of bottom edge.
    right_x : float
        X-coordinate of right edge.
    top_y : float
        Y-coordinate of top edge.
    orientation : {'horizontal', 'vertical'}
        Orientation of the rectangle.
    purpose : str
        Layer purpose of the rectangle.

    Attributes
    ----------
    centroid
    center
    layer : str
        Layout layer the rectangle exists on.
    coords : list[float]
        Rectangle coordinates. List follows the format of [left_x, bot_y,
        right_x, top_y].
    purpose : str
        Layer purpose of the rectangle.
    orientation : {'horizontal', 'vertical'}
        Orientation of the rectangle.

    """
    def __init__(self, layer, left_x, bot_y, right_x, top_y, orientation=None, purpose=['drawing']):
        self.layer = layer
        # Fixme: May want to change these rounding precisions to be a parameter
        self.coords = [round(left_x, 3), round(bot_y, 3), round(right_x, 3), round(top_y, 3)]
        self.purpose = purpose
        self.orientation = orientation

    def scale(self, scale_factor):
        coord_arr = np.asarray(self.coords) * scale_factor
        self.coords = coord_arr.tolist()

    @property
    def centroid(self):
        """
        Centroid of the rectangle.
        Returns
        -------
        tuple(float, float)
            Coordinates of the rectangle's centroid.
        """
        return (round((self.coords[0] + self.coords[2]) / 2, 3), round((self.coords[1] + self.coords[3]) / 2, 3))

    @property
    def center(self):
        """
        Center coordinate of the rectangle. Depending on the orientation,
        this could be either the x or y coordinate

        Returns
        -------
        float
            Center of the rectangle on the relevant side depending on
            orientation. If orientation not specified, returns the centroid.
        """
        if self.orientation == 'horizontal':
            return self.centroid[1]
        elif self.orientation == 'vertical':
            return self.centroid[0]
        else:
            return self.centroid

class Label:
    """
    Representation of a physical label object.

    Parameters
    ----------
    text : str
        Text to be displayed on the label.
    layer : str
        Layout layer the label exists on.
    postiion : list[float, float], tuple(float, float)
        Coordinates for label location.
    show : bool
        True if label to actually be drawn. Default is True.

    Attributes
    ----------
    text : str
    purpose : str
    layer : str
    coords : list[float, float]
    show : bool

    """
    def __init__(self, text, layer, position, show=True):
        self.text = text
        self.purpose = ['label']
        self.layer = layer
        self.coords = [round(position[0], 3), round(position[1], 3)]
        self.show = show

    def scale(self, scale_factor):
        """
        Scales location coordinates by given scale factor.

        Parameters
        ----------
        scale_factor : float
            Scaling factor to apply to coordinates.

        Returns
        -------

        """
        coord_arr = np.asarray(self.coords) * scale_factor
        self.coords = coord_arr.tolist()

class PHYObject:
    """
    Generic Physical Object class. Parent to all other complex physical
    objects.

    Parameters
    ----------
    name : str
        Name of the object.

    Attributes
    ----------
    name : str
        Name of the object.
    purpose : str
        Layer purpose of the object.
    phys_objs : list
        List of Primitive physical objects or Generic physical objects
        that ths object contains.
    rects : dict
        Dictionary of Rectangle objects. Keyed by center coordinate value.
    """
    def __init__(self, name):
        self.name = name
        self.purpose = None
        self.phys_objs = []
        self.rects = {}

    def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0, purpose=['drawing']):
        """
        Adds a Rectangle object to the list of child objects.

        Parameters
        ----------
        layer : str
        left_x : float
            X-coordinate of the left edge.
        bot_y : float
            Y-coordinate of the bottom edge.
        right_x : float
            X-coordinate of the right edge.
        top_y : float
            Y-coordinate of the top edge.
        purpose : str
            Layer purpose of the Rectangle.

        Returns
        -------

        """
        rect_obj = Rectangle(layer, left_x, bot_y, right_x, top_y, purpose=purpose)
        self.phys_objs.append(rect_obj)
        self.rects[rect_obj.centroid] = rect_obj

    def scale(self, scale_factor):
        """
        Scales all objects associated with Pin by scale factor.

        Parameters
        ----------
        scale_factor : float
            Factor by which to scale all physical objects in this Pin.

        Returns
        -------

        """
        for phy_obj in self.phys_objs:
            phy_obj.scale(scale_factor)


class PHYPortPin(PHYObject):
    """
    Port Pin PHYObject.

    Parameters
    ----------
    pin_dict : dict
        Pin descriptor dictionary. This dictionary will contain all the
        relevant information regarding the pin direction, related power/
        ground pins, and pin name.
    layer : str
        Layer the Pin object exists on.
    side : str
        Side of the design that the pin should exist on.
    x_width : float
        X dimension width of the pin shape.
    y_width : float
        Y dimension width of the pin shape.
    center : float, optional
        Center coordinate of the pin. Whether this is an X or Y coordinate
        depends on side. This option actually doesn't serve any purpose.
    bus_idx : int, optional
        Index of bus element that this pin represents. This is only needed
        if the pin is part of a bus. This index is appended onto the name
        of the pin for labeling.

    Attributes
    ----------
    pin_dict : dict
        Pin descriptor dictionary. This dictionary will contain all the
        relevant information regarding the pin direction, related power/
        ground pins, and pin name.
    name : str
        Name of the pin.
    direction : {'input', 'output', 'inout'}
        Port direction of pin.
    layer : str
        Layer the Pin object exists on.
    side : str
        Side of the design that the pin should exist on.
    x_width : float
        X dimension width of the pin shape.
    y_width : float
        Y dimension width of the pin shape.
    center : float
        Center coordinate of the pin.
    related_power_pin : str
        Name of the related power pin to this pin.
    related_ground_pin : str
        Name of the related ground pin to this pin.
    bus_idx : int
        Index of bus element that this pin represents. This is only needed
        if the pin is part of a bus. This index is appended onto the name
        of the pin for labeling.
    block_structure : dict
        This attribute is not used.
    labels : list[Label]
        List of Label objects associated with this pin object.
    """
    def __init__(self, pin_dict, layer, side, x_width, y_width, center=None, bus_idx=None):
        super().__init__(pin_dict['name'])

        self.pin_dict = pin_dict
        self.direction = pin_dict['direction']
        self.layer = layer
        self.side = side
        self.x_width = x_width
        self.y_width = y_width
        self.center = center
        self.related_power_pin = pin_dict.get('power_pin', None)
        self.related_ground_pin = pin_dict.get('ground_pin', None)
        # self.is_bus = pin_dict.get("is_bus", False)
        if isinstance(bus_idx, int):
            self.bus_idx = bus_idx
            self.name = self.name + f'[{self.bus_idx}]'
        self.block_structure = {}
        self.labels = []

    def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0, purpose=['drawing', 'pin']):
        """
        Adds a Rectangle object to list of objects. This is different from
        parent method add_rect in that this method calculates upper right
        coordinate from x/y width attributes.

        Parameters
        ----------
        layer : str
            Layout layer the Rectangle exists on.
        left_x : float
            X-coordinate of the left edge.
        bot_y : float
            Y-coordinate of the bottom edge.
        right_x : float
            X-coordinate of the right edge.
        top_y : float
            Y-coordinate of the top edge.
        purpose : str
            Layer purpose of the Rectangle.

        Returns
        -------

        """
        right_x = left_x + self.x_width
        top_y = bot_y + self.y_width
        orientation = 'horizontal' if self.side in ['left', 'right'] else 'vertical'
        rect_obj = Rectangle(layer, left_x, bot_y, right_x, top_y, orientation, purpose=purpose)
        if rect_obj.center not in self.rects.keys():
            self.phys_objs.append(rect_obj)
            self.rects[rect_obj.center] = rect_obj
            self.add_label(layer, ((right_x + left_x) / 2, (top_y + bot_y) / 2))

    def add_label(self, layer, position):
        """
        Adds a Label object to the pin.

        Parameters
        ----------
        layer : str
            Layout layer the Label exists on.
        position : list[float, float], tuple(float, float)
            Coordinates of the Label object.

        Returns
        -------

        """
        label_obj = Label(self.name, layer, position, show=True)
        self.phys_objs.append(label_obj)
        self.labels.append(label_obj)


# class PHYBBox(PHYObject):
#     def __init__(self, layers, left_x, bot_y, right_x, top_y):
#         super().__init__("BBOX")
#         self.purpose = 'blockage'
#         for layer in layers:
#             self.add_rect(layer, left_x, bot_y, right_x, top_y)
#
#     def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0, purpose=['blockage']):
#         rect_obj = Rectangle(layer, left_x, bot_y, right_x, top_y, purpose=purpose)
#         self.phys_objs.append(rect_obj)
#         self.rects[rect_obj.centroid] = rect_obj
#
#     def scale(self, scale_factor):
#         for rect in self.phys_objs:
#             rect.scale(scale_factor)

class PHYDesign:
    """Python representation of a PHY Design. Right now this just consumes
    VerilogModules.

    Parameters
    ----------
    verilog_module : VerilogModule
        VerilogModule object that will be processed into a PHYDesign.
    techfile : str, Path
        Path to the tech.json for the technology the PHYDesign is to be
        made in.
    spec_dict : dict
        Dictionary of options and specifications for the design. Please
        consult spec_dict_schema.yaml for an example of the spec_dict
        schema.

    Attributes
    ----------
    verilog_pin_dict : dict
    verilog_pg_pin_dict : dict
    name : str
    spec_dict : dict
    pins : list[PHYPortPin]
    pg_pins :


    """

    def __init__(self, verilog_module, techfile, spec_dict=None):
        self.verilog_pin_dict = verilog_module.pins
        self.verilog_pg_pin_dict = verilog_module.power_pins
        self.name = verilog_module.name

        techfile = str(techfile) if not isinstance(techfile, str) else techfile
        filetype = techfile.split('.')[-1].lower()  # This normally expects a HAMMER tech.json
        if filetype == 'json':
            self._extract_tech_json_info(techfile)
        elif filetype == 'yaml' or filetype == 'yml':
            raise NotImplementedError
        else:
            raise ValueError(f"Unrecognized File Type .{filetype}")

        self.spec_dict = spec_dict
        self.pins = []
        self.pg_pins = []
        self.phys_objs = []
        self.defaults = {'origin': [0, 0],
                         'units': 1e-6,
                         'precision': 1e-9,
                         'input_side': 'left',
                         'output_side': 'right',
                         'pin_margin': False,
                         'symmetry': 'X Y',
                         'site': 'core',
                         'design_boundary' : (10,10),
                         'bound_box': [0, 0, 10, 10],
                         'pins': {'h_layer': "M2",
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
        self.specs = Specification(self.defaults)
        if spec_dict:
            self.specs.data = r_update(self.specs.data, spec_dict)
        self.x_width = self.specs.data.get('xwidth', None)
        self.y_width = self.specs.data.get('ywidth', None)
        # self.aspect_ratio = self.specs_dict.get('aspect_ratio', None)
        self.polygons = {'pins': self.pins,
                         'pg_pins': self.pg_pins}

    def _extract_tech_json_info(self, techfile):
        with open(techfile) as file:
            self.tech_dict = json.load(file)
        stackups = self.tech_dict['stackups'][0]['metals']
        self.metals = {}
        for layer in stackups:
            self.metals[layer['name']] = layer

    def add_pg_pin_objects(self):
        """

        ..deprecated : 0.9
            This method has been superceded by the pin placer.

        Returns
        -------

        """
        power_pin_name = self.verilog_pg_pin_dict['power_pin']
        ground_pin_name = self.verilog_pg_pin_dict['ground_pin']
        pg_pin_specs = self.specs.data['pg_pins']
        pwr_pin_specs = self.specs.data['pg_pins']['pwr_pin']
        gnd_pin_specs = self.specs.data['pg_pins']['gnd_pin']



        if pwr_pin_specs['side'] == 'top' or pwr_pin_specs['side'] == 'bottom':
            if not pwr_pin_specs.get('xwidth', None):
                pwr_pin_specs['xwidth'] = self.metals[pg_pin_specs['v_layer']]['min_width']
            if not pwr_pin_specs.get('ywidth', None):
                pwr_pin_specs['ywidth'] = self.specs.data['pins']['pin_length']
        else:
            if not pwr_pin_specs.get('ywidth', None):
                pwr_pin_specs['ywidth'] = self.metals[pg_pin_specs['v_layer']]['min_width']
            if not pwr_pin_specs.get('xwidth', None):
                pwr_pin_specs['xwidth'] = self.specs.data['pins']['pin_length']

        if gnd_pin_specs['side'] == 'top' or gnd_pin_specs['side'] == 'bottom':
            if not gnd_pin_specs.get('xwidth', None):
                gnd_pin_specs['xwidth'] = self.metals[gnd_pin_specs['h_layer']]['min_width']
            if not gnd_pin_specs.get('ywidth', None):
                gnd_pin_specs['ywidth'] = self.specs.data['pins']['pin_length']
        else:
            if not gnd_pin_specs.get('ywidth', None):
                gnd_pin_specs['ywidth'] = self.metals[gnd_pin_specs['h_layer']]['min_width']
            if not gnd_pin_specs.get('xwidth', None):
                gnd_pin_specs['xwidth'] = self.specs.data['pins']['pin_length']

        pwr_pin_dict = {'name': power_pin_name,
                        'direction': 'inout',
                        'is_analog': False}
        gnd_pin_dict = {'name': ground_pin_name,
                        'direction': 'inout',
                        'is_analog': False}
        pwr_pin = PHYPortPin(pwr_pin_dict, pwr_pin_specs['layer'],
                             pwr_pin_specs['side'],
                             round(pwr_pin_specs['xwidth'], 3),
                             round(pwr_pin_specs['ywidth'], 3),
                             center=pg_pin_specs['pwr_pin'].get('center', None))
        gnd_pin = PHYPortPin(gnd_pin_dict, pg_pin_specs['gnd_pin']['layer'],
                             pg_pin_specs['gnd_pin']['side'],
                             round(pg_pin_specs['gnd_pin']['xwidth'], 3),
                             round(pg_pin_specs['gnd_pin']['ywidth'], 3),
                             center=pg_pin_specs['gnd_pin'].get('center', None))
        pwr_pin.type = 'POWER'
        gnd_pin.type = 'GROUND'
        self.pg_pins['pwr'] = pwr_pin
        self.pg_pins['gnd'] = gnd_pin
        self.phys_objs.append(pwr_pin)
        self.phys_objs.append(gnd_pin)

    def add_pin_objects(self):
        self.n_inputs = 0
        self.n_outputs = 0
        for pin_name, pin_info in self.verilog_pin_dict.items():
            pin_spec = self.specs.data['pins'].get(pin_name, None)
            direction = pin_info['direction']
            # Pin side definitions
            if pin_spec:
                side = pin_spec.get('side', None)
            else:
                side = None
            if not side:
                side = self.specs.data.get(f'{direction}_side', None)
            if not side:
                side = self.specs.data['input_side'] if direction == 'input' else self.specs.data['output_side']

            # Pin Layer definitions
            if side == 'left' or side == 'right':
                layer = self.specs.data['pins']['h_layer']
                if pin_spec:
                    x_width = pin_spec.get('x_width', self.specs.data['pins']['pin_length'])
                    y_width = pin_spec.get('y_width', self.metals[layer]['min_width'])
                else:
                    x_width = self.specs.data['pins']['pin_length']
                    y_width = self.metals[layer]['min_width']
            else:
                layer = self.specs.data['pins']['v_layer']
                if pin_spec:
                    x_width = pin_spec.get('x_width', self.specs.data['pins']['pin_length'])
                    y_width = pin_spec.get('y_width', self.metals[layer]['min_width'])
                else:
                    x_width = 'x_width', self.specs.data['pins']['pin_length']
                    y_width = 'y_width', self.metals[layer]['min_width']
            if pin_info.get('is_bus', None):
                self.n_inputs += (direction == 'input') * (pin_info['bus_max'] + 1)
                self.n_outputs += (direction == 'output') * (pin_info['bus_max'] + 1)
                for pin in range(pin_info['bus_max'] + 1):
                    self.pins[pin_name + '[' + str(pin) + ']'] = PHYPortPin(pin_info, layer, side, round(x_width, 3),
                                                                            round(y_width, 3),
                                                                            bus_idx=pin)
            else:
                self.n_inputs += direction == 'input'
                self.n_outputs += direction == 'output'
                self.pins[pin_name] = PHYPortPin(pin_info, layer, side, round(x_width, 3), round(y_width, 3))
        self.phys_objs += list(self.pins.values())

    def define_design_boundaries(self):
        pass

    def scale(self, scale_factor = 1):
        scaled = []
        for obj in self.phys_objs:
            obj.scale(scale_factor)

        self.x_width = round(self.x_width * scale_factor, 3)
        self.y_width = round(self.y_width * scale_factor, 3)

