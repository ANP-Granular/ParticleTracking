import torch

if __name__ == "__main__":

    model = torch.hub.load(
        "ANP-Granular/ParticleTracking:develop", "model", pretrained=True
    )
    print(model)
