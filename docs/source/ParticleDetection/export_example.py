from pathlib import Path
import torch
from ParticleDetection.modelling import export


def test_export(version: str):
    model = torch.jit.load(f"./model_{version}.pt")
    sample = Path("./your_dataset/test_image.jpg")
    input = export.get_sample_img(sample)
    with torch.no_grad():
        testing = model.forward(input)
    print(testing)


version = "cpu"
config = Path("./your_model/config.yaml").resolve()
weights = Path("./your_model/model_final.pth").resolve()
sample = Path("./your_dataset/test_image.jpg")
export.export_model(config, weights, sample, version)
test_export(version)
