from pathlib import Path
from reconstruct_3D import randomize_data

rnd_seed = 1


def randomize_3dblue():
    data_p = Path("../../datasets/100-904_3Dt_13_blue/"
                  "rods_df_blue.csv").resolve()
    randomize_data.randomize_particles(data_p)
    randomize_data.randomize_endpoints(data_p)
    randomize_data.randomize_particles(data_p.parent / ("rand_endpoints_" +
                                                        str(data_p.name)))


if __name__ == "__main__":
    randomize_3dblue()
