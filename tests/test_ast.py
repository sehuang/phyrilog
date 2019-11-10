from verilog_pin_extract import VerilogModule, NameLookup
import os, pathlib, ast
from resources.astpp import parseprint
import pprint as pp


this_path = os.path.abspath('')
projects_dir = pathlib.Path(this_path).parents[1]
behav_model = projects_dir / 'phyrilog/views2/behavioral/sram.v'
# behav_model = projects_dir / 'phyrilog/src/sram_behav_models.v'
consts = projects_dir / 'phyrilog/views2/behavioral/const.vh'
asap7_layermapfile = projects_dir / 'phyrilog/asap7_TechLib.layermap'
techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
corners = projects_dir / 'phyrilog/resources/asap7_lib_corners.json'

if __name__ == '__main__':
    sram256x32 = VerilogModule('SRAM1RW256x32', filename=behav_model, constfile=consts)
    pp.pprint(sram256x32.pins)

    # string = 'numAddr-1'
    #
    # class foo:
    #     def __init__(self):
    #         self.params={'numAddr': 5}
    #
    #     def ast_parse_thing(self, string):
    #         clean_exp = string
    #         expr_ast = ast.parse(clean_exp, mode='eval')
    #         elaborated_ast = NameLookup().visit(expr_ast)
    #         ast.fix_missing_locations(elaborated_ast)
    #         parseprint(expr_ast)
    #         print("")
    #         parseprint(elaborated_ast)
    #         return eval(compile(elaborated_ast, filename="sdsd", mode='eval'))
    #
    # thing = foo()
    # print(thing.ast_parse_thing(string))