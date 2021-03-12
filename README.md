# phyrilog
Verilog-to-physical conversion scripts

This package accepts a Verilog file and collateral headers and generates an
internal physical representation of the design, which it translates to a LEF,
LIB, and GDS view.

Note that this generates a black box blockage and does not contain any layout within the view.
The views generated with this package will not pass signoff and are merely for verifying physical
design flows before receiving actual IP.

## ASAP7 SRAM View Generation
Relevant scripts live in the `scripts` directory.

To generate the SRAM views, run `generate_srams.py`. This finds all SRAM types
defined in the behavioral model and performs the physical view generation for each one.

To modify the parameters in the generation, the relevant object classes are in `gen_srams.py`

### `gen_srams.py`
This file contains three class structures, `SRAMBBox`, `ASAP7Characterizer` and `ASAP7SRAMs`.

#### `SRAMBBox`
This class represents the per-instance physical representation for each SRAM instance. Methods
for determining design width and aspect ratio, as well as options for the view generation itself
live here and are shared across all SRAM instances. If you need custom settings for a particular
SRAM instance, this can be subclassed for those cases.

The `_get_xwidth_from_*` methods are the most arbitrary here, where I just picked some scale factor
for the xwidth based on the word length and address width of the SRAM. This will directly affect
the SRAM dimensions, so these should probably be the first methods to be modified for tweaking SRAM
generation.

#### `ASAP7Characterizer`
This is a characterizer for the dotlibber when generating LIBs for the SRAMs. The characterizer formulas
are completely arbitrary and were the result of me doing a very rough manual curve fit to sort of emulate
the characteristics of another SRAM lib, with scaling from technology.

#### `ASAP7SRAMs`
This is a container object for all the SRAMs generated from the behavioral file. This class just contains
wrapper methods for creating the `SRAMBBox` instances and abstracts the behavioral file scraping to a few
"make/build objs" APIs. This is just to streamline the script in `generate_srams.py`.
