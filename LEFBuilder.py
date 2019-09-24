from verilog2lef import PHYDesign


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

    def add_block(self, parent, type, name, lines):
        """LEF Blocks are usually grouped under similar indentation"""
        if not parent.get('blocks', None):
            parent['blocks'] = {}
        if not parent['blocks'].get(type, None):
            parent['blocks'][type] = [{}]
        parent['blocks'][type].append({'name': name,
                                       'lines': lines})

    def add_rect(self, parent, corners=None):
        parent['blocks']

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

    def make_lef(self, thing: PHYDesign):
        pins = thing.pins
        bbox = thing.bbox
        name = thing.name
        header_lines = self.add_lef_header(version=5.6)
        origin_line = f"ORIGIN {thing.specs['origin'][0]} {thing.specs['origin'][1]}"
        size_line = f"SIZE {thing.x_width} BY {thing.y_width}"
        sym_line = f"SYMMETRY {thing.specs['symmetry']}"
        site_line = f"SITE {thing.specs['site']}"
