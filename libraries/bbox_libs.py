from GDSBuilder import *
from LEFBuilder import *
from verilog2phy import *
from pin_placer import *


class PHYBBox(PHYObject):
    def __init__(self, layers, left_x, bot_y, x_width, y_width):
        super().__init__("BBOX")
        self.purpose = 'blockage'
        for layer in layers:
            self.add_rect(layer, left_x, bot_y, left_x + x_width, bot_y + y_width)

    def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0, purpose=['blockage']):
        rect_obj = Rectangle(layer, left_x, bot_y, right_x, top_y, purpose=purpose)
        self.phys_objs.append(rect_obj)
        self.rects[rect_obj.centroid] = rect_obj

    def scale(self, scale_factor):
        for rect in self.phys_objs:
            rect.scale(scale_factor)

class BBoxPHY(PHYDesign):
    """Black-boxed LEF object. This class describes LEF stuff"""

    def __init__(self, verilog_module, techfile, spec_dict=None):
        self.strictness_opt = ['flexible', 'strict']
        self.bbox_defaults = {'aspect_ratio_strictness': 'strict',
                              'x_strictness': 'strict',
                              'y_strictness': 'flexible'
                              }
        specs = r_update(self.bbox_defaults, spec_dict)
        super().__init__(verilog_module, techfile, specs)
        # self.add_pin_objects()
        # self.add_pg_pin_objects()
        # self.build_design_repr()
        self.pin_specs = self.specs['pins']
        self.pin_specs = r_update(self.pin_specs, self.specs['pg_pins'])
        self.pin_placer = PinPlacer(verilog_module.pins, verilog_module.power_pins, techfile,
                                    pin_specs=self.pin_specs, options_dict=spec_dict)
        self.define_design_boundaries()
        self.build_design_repr()

    def define_design_boundaries(self):
        if 'y_width' in self.specs.keys() or 'x_width' in self.specs.keys():
            x_width = self.specs.get('x_width', 0)
            y_width = self.specs.get('y_width', 0)
            if 'aspect_ratio' in self.specs.keys():
                ar = self.specs['aspect_ratio']
                if y_width and not x_width:
                    x_width = round(y_width / ar[1] * ar[0], 3)
                elif x_width and not y_width:
                    y_width = round(x_width / ar[1] * ar[0], 3)
                else:
                    if self.specs['x_strictness'] == self.strictness_opt[0]:
                        x_width = round(y_width / ar[1] * ar[0], 3)
                    elif self.specs['y_strictness'] == self.strictness_opt[0]:
                        y_width = round(x_width / ar[1] * ar[0], 3)
                    else:
                        raise ValueError(
                            "Cannot resolve aspect ratio with given x and y widths. \
                            Please relax the definition or strictness for a dimension.")

                if x_width < self.pin_placer.min_x_dim:
                    if self.specs['x_strictness'] == self.strictness_opt[1]:
                        raise ValueError(
                            f'Given x width {x_width} is less than minimum x width \
                            {self.pin_placer.min_x_dim} needed to successfully place pins.\
                             Please adjust dimension or relax x strictness.')
                    else:
                        x_width = self.pin_placer.min_x_dim
            if y_width < self.pin_placer.min_y_dim:
                if self.specs['y_strictness'] == self.strictness_opt[1]:
                    raise ValueError(
                        f'Given y width {y_width} is less than minimum y width \
                        {self.pin_placer.min_y_dim} needed to successfully place pins.\
                         Please adjust dimension or relax y strictness.')
                else:
                    y_width = self.pin_placer.min_y_dim
            self.bbox_x_width = round(x_width, 3)
            self.bbox_y_width = round(y_width, 3)
            bbox = np.asarray([round(self.pin_placer.max_l_pin_length, 3),
                               round(self.pin_placer.max_b_pin_length, 3),
                               round(x_width + self.pin_placer.max_l_pin_length, 3),
                               round(y_width + self.pin_placer.max_b_pin_length, 3)])
            bbox = np.asarray(self.pin_placer.specs['origin'] * 2) + bbox
            self.pin_placer.specs['internal_box'] = bbox.tolist()
            if self.specs['pin_margin']:
                margins = np.asarray([0, 0, self.pin_placer.v_pin_pitch,
                                      self.pin_placer.h_pin_pitch])
                inner_box = bbox + margins
                self.pin_placer.specs['internal_box'] = inner_box.tolist()
            self.pin_placer.specs['design_boundary'] = (self.pin_placer.specs['internal_box'][
                                                            2] + self.pin_placer.max_r_pin_length,
                                                        self.pin_placer.specs['internal_box'][
                                                            3] + self.pin_placer.max_t_pin_length)
            self.pin_placer.specs['bound_box'] = self.pin_placer.specs['origin'] + list(self.pin_placer.specs['design_boundary'])
        else:
            self.pin_placer.autodefine_boundaries()
            self.bbox_x_width =  self.pin_placer.specs['internal_box'][2] - self.pin_placer.specs['internal_box'][0]
            self.bbox_y_width = self.pin_placer.specs['internal_box'][3] - self.pin_placer.specs['internal_box'][1]
        # Update local specs to reflect pin_placer specs
        self.specs = r_update(self.specs, self.pin_placer.specs)

    def place_pins(self):
        self.pin_placer.place_pins()
        self.pins = self.pin_placer.pins
        self.pg_pins = self.pin_placer.pg_pins
        self.pin_sides_dict = self.pin_placer.pin_sides_dict
        self.partitions = self.pin_placer.partitions
        self.phys_objs += self.pins
        self.phys_objs += self.pg_pins.values()

    def build_design_repr(self):
        bbox_layers = []
        for layer in self.metals:
            if layer not in self.specs['exclude_layers']:
                bbox_layers.append(layer)
        self.bboxes = {
            'BBOX': PHYBBox(bbox_layers,
                            self.specs['internal_box'][0],
                            self.specs['internal_box'][1],
                            self.bbox_x_width,
                            self.bbox_y_width)}
        self.polygons['bboxes'] = self.bboxes
        self.phys_objs.append(self.bboxes['BBOX'])

class BBoxLEFBuilder(LEFBuilder):

    def __init__(self, phy_design, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.make_lef_dict(phy_design)

    def make_lef_dict(self, phy_design: PHYDesign, add_pg_pins=True):
        pins = phy_design.pins
        bbox = phy_design.bboxes
        pg_pins = phy_design.pg_pins
        name = phy_design.name
        class_line = "CLASS BLOCK"
        header_lines = self.add_lef_header(version=5.6)
        origin_line = f"ORIGIN {phy_design.specs['origin'][0]} {phy_design.specs['origin'][1]}"
        foreign_line = f"FOREIGN {name} {phy_design.specs['origin'][0]} {phy_design.specs['origin'][1]}"
        size_line = f"SIZE {phy_design.x_width} BY {phy_design.y_width}"
        sym_line = f"SYMMETRY {phy_design.specs['symmetry']}"
        site_line = f"SITE {phy_design.specs['site']}"

        self.lines += header_lines
        self.lines += '\n'

        # Macro lines
        macro_lines = [class_line, origin_line, foreign_line, size_line, sym_line, site_line]

        macro_block = self.add_block('MACRO', phy_design.name, lines=macro_lines)
        if add_pg_pins:
            for pg, pin in pg_pins.items():
                macro_block.add_pgpin(pg, pin)
        for pin in pins:
            macro_block.add_pin(pin)
        for bbox in bbox.values():
            macro_block.add_bbox_obs(bbox.phys_objs)
