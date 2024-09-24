# Optional list of dependencies required by the package
dependencies = ["torch"]

example_model_url = "https://zenodo.org/records/10255525/files/model_cpu.pt?download=1"


def rods_example_model(pretrained: bool = False, progress: bool = False, **kwargs: Any):

    model: torch.ScriptModule = None
    if pretrained:
        state_dict = torch.hub.load_state_dict_from_url(
            example_model_url, progress=progress
        )
        model.load_state_dict(state_dict)
    return model
