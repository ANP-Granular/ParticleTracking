import sys
from enum import Enum
from pathlib import Path
from types import ModuleType
import numpy as np
not_installed = False
try:
    from ParticleDetection.modelling.runners import detection
except ModuleNotFoundError:
    not_installed = True
    # Mock imports of detectron2 modules to allow running of function tests,
    # that don't depend on them.
    module = ModuleType("detectron2")
    module.model_zoo = None
    submod0 = ModuleType("engine")
    submod0.DefaultPredictor = None
    submod1 = ModuleType("utils")
    subsubmod0 = ModuleType("logger")
    subsubmod0.setup_logger = None
    submod2 = ModuleType("config")
    submod2.CfgNode = None
    submod2.get_cfg = None
    sys.modules["detectron2"] = module
    sys.modules["detectron2.engine"] = submod0
    sys.modules["detectron2.utils"] = submod1
    sys.modules["detectron2.utils.logger"] = subsubmod0
    sys.modules["detectron2.config"] = submod2

    module2 = ModuleType("configs")
    module2.write_configs = None
    sys.modules["ParticleDetection.modelling.configs"] = module2

    submod3 = ModuleType('structures')
    submod3.BoxMode = Enum("BoxMode", ["XYXY_ABS", ])
    sys.modules["detectron2.structures"] = submod3
    submod4 = ModuleType("data")
    submod4.DatasetCatalog = None
    submod4.MetadataCatalog = None
    sys.modules["detectron2.data"] = submod4

    submod5 = ModuleType('visualizer')
    submod5.GenericMask = None
    sys.modules["detectron2.utils.visualizer"] = submod5
finally:
    from ParticleDetection.modelling.runners import detection


def test_save_to_mat(tmp_path: Path):
    test_points = {i: np.random.random((i + 1, 2, 2)) for i in range(10)}
    detection.save_to_mat(str(tmp_path / "test"), test_points)
    assert len(list(tmp_path.iterdir())) == len(test_points)
