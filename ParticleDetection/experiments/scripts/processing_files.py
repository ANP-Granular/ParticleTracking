import os
import ParticleDetection.utils.data_conversions as dc


def combine_assembled_csv():
    base_path = "../../datasets/assembled_200-906_2D"
    colors = [
        "blue", "brown", "green", "lilac", "orange", "purple", "red", "yellow",
    ]
    files = [os.path.join(base_path, f"rods_df_{c}.csv")for c in colors]
    print(dc.csv_combine(files))


if __name__ == "__main__":
    combine_assembled_csv()
