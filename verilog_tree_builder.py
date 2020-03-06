


class Wire:
    def __init__(self, name, parent=None, children=()):
        self.name = name
        self.parent = parent
        self.children = [el for el in children]
        self._seq = None
        self._root = None
        # if parent:
        #     self._root = self.parent.root
        # else:
        #     self._root = self


    def add_child(self, node):
        self.children.append(node)

    def add_parent(self, node):
        # This method should never be used
        self.parent = node
        self._root = self.parent.root

    @property
    def seq(self):
        if not self.parent and not isinstance(self._seq, bool):
            self._seq = False
        else:
            self._seq = self.parent.seq
        return self._seq

    @seq.setter
    def seq(self, val):
        self._seq = val

    @property
    def root(self):
        if self._root:
            return self._root
        if self.parent:
            self._root = self.parent.root
        else:
            self._root = self


class Reg(Wire):
    def __init__(self, name, parent=None, children=()):
        super().__init__(name, parent, children)
        self._seq = True


class Block:
    def __init__(self, periphery, body):
        self.periphery = periphery
        self.body = body


class BlockBody:
    """
    Block Body connection object (mainly important for Always blocks)

    Parameters
    ----------
    conn_list : List[Tuple]
        List of connection tuples. The first element in the tuple is the
        parent connection, and the second is the child.
    """
    def __init__(self, conn_list):
        self.conn_list = conn_list
        self.inputs = []
        self.outputs = []
        for conn in conn_list:
            self.outputs.append(conn[1])


class Always(Block):
    def __init__(self, periphery, body, edge=False):
        super().__init__(periphery, body)
        self.edge = edge
        # for el in body.outputs:
        #     el.seq = True


class Module(Block):
    def __init__(self, name, periphery, body):
        super().__init__(periphery, body)
        self.name = name
        self.inputs = []
        self.outputs = []
        for port in periphery:
            if port.direction == 'input':
                self.inputs.append(port)
            elif port.direction == 'output':
                self.outputs.append(port)
            else:
                raise ValueError(f"Undefined port direction for port {port.name}.")
        self.submodules = []
        self.a_blocks = []
        self.wires = self.periphery

    def add_submodule(self, submodule):
        self.submodules.append(submodule)
        for port in submodule.periphery:
            self.wires.append(port)

    def add_always_block(self, always_block):
        self.a_blocks.append(always_block)
        # self.wires += always_block.periphery

    def add_wire(self, wire):
        self.wires.append(wire)

    #     self.process_body()
    #
    # def process_body(self):
    #     for conn in self.body.conn_list:




class Port(Wire):
    def __init__(self, name, direction, parent=None, children=()):
        super().__init__(name, parent, children)
        self.name = name
        self.direction = direction


class VerilogDB:
    def __init__(self):
        self.wires = {}
        self.modules = {}


class VerilogTree:
    def __init__(self, top):
        self.curlvl = 0


    def

