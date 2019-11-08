from scripts.gen_srams import ASAP7SRAMs
import pathlib
import os

if __name__ == '__main__':
    this_path = os.path.abspath('')
    projects_dir = pathlib.Path(this_path).parents[1]
    behav_model = projects_dir / 'phyrilog/views2/behavioral/sram.v'
    # behav_model = projects_dir / 'phyrilog/src/sram_behav_models.v'
    consts = projects_dir / 'phyrilog/views2/behavioral/const.vh'
    asap7_layermapfile = projects_dir / 'phyrilog/asap7_TechLib.layermap'
    techfile = projects_dir / 'hammer/src/hammer-vlsi/technology/asap7/asap7.tech.json'
    corners = projects_dir / 'phyrilog/resources/asap7_lib_corners.json'

    asap7_srams = ASAP7SRAMs(behav_model, projects_dir / 'phyrilog', projects_dir / 'hammer')
    asap7_srams.add_all_srams()
    asap7_srams.build_all_srams()