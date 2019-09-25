from verilog2lef import PHYDesign

class LEFBlock:
    def __init__(self, type, lines):
        self.type = type
        self.lines = lines
        self.blocks = {}

class LEFBuilder:
    """API for ease of building a LEF file."""

    def __init__(self, filename=None, path=None):
        self.lines = []
        self.blocks = {}
        self.lef = ""
        self.filename = filename
        self.path = path

    def add_lef_header(self, version=None, bus_bit_chars="[]", divider_char="/"):
        lines = []
        lines.append(f"VERSION {version}")
        lines.append("BUSBITCHARS " + "\"" + str(bus_bit_chars) + "\"")
        lines.append("DIVIDERCHAR " + "\"" + str(divider_char) + "\"")
        return lines

    def add_block(self, parent, block_type, name, lines):
        """LEF Blocks are usually grouped under similar indentation"""
        if not parent.get('blocks', None):
            parent['blocks'] = {}
        if not parent['blocks'].get(block_type, None):
            parent['blocks'][block_type] = []
        parent['blocks'][block_type].append({'name': name,
                                       'lines': lines})

    def add_layer(self, parent, layer_name, layer_list):
        if not parent.get('layers', None):
            parent['layers'] = {}
        if not parent['layers'].get(layer_name, None):
            parent['layers'][layer_name] = {}
        for rect in layer_list:
            self.add_rect(parent[layer_name], rect)

    def add_port(self, parent, pin_phys_map):
        self.add_block(parent, 'PORT', '', [])
        for layer_name, layer_list in pin_phys_map.items():
            self.add_layer(parent, layer_name, layer_list)

    def add_rect(self, parent, corners):
        coords = " ".join(corners)
        if not parent.get('rects', None):
            parent['rects'] = []
        parent['rects'].append("RECT " + coords)

    def add_pin(self, parent, name, pin_obj):
        lines = []
        lines.append(f"DIRECTION {pin_obj.direction.upper()}")
        lines.append(f"USE SIGNAL")
        self.add_block(parent, 'PIN', name, lines)
        self.add_port(parent['PIN'][-1], pin_obj.phys_map)

    # def add_pin(self, parent, name, lines):

    # def add_macro(self, name, lines):
    #     parent = self.blocks


    def build_block(self, block, level):
        str_out = ""
        for block_type in block.keys():
            for block_dict in block[block_type]:
                block_header = '\t' * (level + 1) + block_type + " " + block_dict['name'] + '\n'
                str_out += block_header
                for line in block_dict['lines']:
                    str_out += '\t' * (level + 1) + line + " ;\n"
                if block.get('blocks', None):
                    for block in block['blocks']:
                        str_out += self.build_block(block, level + 1)
        return str_out

    def build_lef(self):
        for line in self.lines:
            self.lef += line + " ;\n"



# def add_pin


class BBoxLEFBuilder(LEFBuilder):

    def __init__(self):
        super().__init__()

    def add_bbox_obs(self, parent, bbox_phys_map):
        self.add_block(parent, 'OBS', '', [])
        for layer_name, layer_list in bbox_phys_map:
            self.add_layer(parent, layer_name, layer_list)

    def make_lef_dict(self, phy_design: PHYDesign):
        pins = phy_design.pins
        bbox = phy_design.bboxes
        name = phy_design.name
        class_line = "CLASS CORE"
        header_lines = self.add_lef_header(version=5.6)
        origin_line = f"ORIGIN {phy_design.specs['origin'][0]} {phy_design.specs['origin'][1]}"
        size_line = f"SIZE {phy_design.x_width} BY {phy_design.y_width}"
        sym_line = f"SYMMETRY {phy_design.specs['symmetry']}"
        site_line = f"SITE {phy_design.specs['site']}"



        # Macro lines
        macro_lines = [class_line, origin_line, size_line, sym_line, site_line]

        self.add_block(self.blocks, 'MACRO', phy_design.name, lines=macro_lines)
        macro_block = self.blocks['MACRO']
        for pin in pins:
            self.add_pin(self.blocks['MACRO'], pin.name, pin)
        for bbox in bbox:
            self.add_bbox_obs(self.blocks['MACRO'])

