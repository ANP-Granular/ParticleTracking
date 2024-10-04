# Optional list of dependencies required by the package
dependencies = ["torch", "os"]

import torch
import os

example_model_cpu_url = (
    "https://zenodo.org/records/10255525/files/model_cpu.pt?download=1"
)
model_cpu_file_name = "model_cpu.pt"

example_model_cuda_url = (
    "https://zenodo.org/records/10255525/files/model_cuda.pt?download=1"
)
model_cuda_file_name = "model_cuda.pt"


def rods_example_model_cpu(pretrained: bool = False, progress: bool = False):

    if pretrained:
        hub_dir = torch.hub.get_dir()
        model_dir = os.path.join(hub_dir, "checkpoints")
        os.makedirs(model_dir, exist_ok=True)
        model_file = os.path.join(model_dir, model_cpu_file_name)

        torch.hub.download_url_to_file(
            example_model_cpu_url, model_file, progress=progress
        )


def rods_example_model_cuda(pretrained: bool = False, progress: bool = False):

    if pretrained:
        hub_dir = torch.hub.get_dir()
        model_dir = os.path.join(hub_dir, "checkpoints")
        os.makedirs(model_dir, exist_ok=True)
        model_file = os.path.join(model_dir, model_cuda_file_name)

        torch.hub.download_url_to_file(
            example_model_cuda_url, model_file, progress=progress
        )
