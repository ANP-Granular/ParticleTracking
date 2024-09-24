import torch

if __name__ == "__main__":

    model = torch.hub.load(
        "ANP-Granular/ParticleTracking:develop",
        "rods_example_model",
        pretrained=True,
    )
    print(model)
