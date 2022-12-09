

# Shamelessly ripping off of the AST module

class Signal:
    def __init__(self, name):
        self.name = name
        self.elaboration = name

class UnaryOp:
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

class NOT:
    def __init__(self, tilde=False):
        if tilde:
            self.elaboration = '~'
        else:
            self.elaboration = '!'

class AND:
    def __init__(self):
        self.elaboration = '&'

class OR:
    def __init__(self):
        self.elaboration = '|'

class BinaryOp:
    def __init__(self, op, operand1, operand2):
        self.op = op
        self.operand1 = operand1
        self.operand2 = operand2
        self.order = [self.operand1,
                      self.op,
                      self.operand2]

    @property
    def elaboration(self):
        return_str = ""
        for el in self.order:
            return_str += el.elaboration
        return return_str

# class Tree:
#     def __init__(self):



# def parse(expr):

#     for char in expr:
#         if