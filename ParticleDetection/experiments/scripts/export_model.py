from typing import List
from pathlib import Path
import torch
from ParticleDetection.modelling import export


def test_export(version: str):
    model = torch.jit.load(f"./model_{version}.pt")
    sample = Path("../../datasets/rods_c4m/train/FT2015_shot1_gp1_00400.jpg")
    input = export.get_sample_img(sample)
    with torch.no_grad():
        testing = model.forward(input)
    print(testing)


def run_exported(model_path: Path, images: List[Path]):
    # Load model
    model = torch.jit.load(str(model_path.resolve()))
    out = []

    for img in images:
        input = export.get_sample_img(img)
        with torch.no_grad():
            ret = model.forward(input)
            out.append({
                "pred_boxes": ret[0],
                "pred_classes": ret[1],
                "pred_masks": ret[2],
                "scores": ret[3],
                "input_size": ret[4],
            })
    return out


if __name__ == "__main__":
    version = "cpu"
    config = Path("../../models/PointRend/config.yaml").resolve()
    weights = Path("../../models/PointRend/model_final.pth").resolve()
    sample = Path("../../datasets/rods_c4m/train/FT2015_shot1_gp1_00400.jpg")
    export.export_model(config, weights, sample, version)
    test_export(version)
