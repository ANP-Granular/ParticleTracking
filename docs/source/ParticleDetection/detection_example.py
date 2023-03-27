from pathlib import Path
import torch

from ParticleDetection.utils import detection
import ParticleDetection.utils.datasets as ds
# Don't remove the following import, see GitHub issue as reference
# https://github.com/pytorch/pytorch/issues/48932#issuecomment-803957396
import cv2
import torchvision
import ParticleDetection

# Setup
cam1 = 1
cam2 = 2
frames = list(range(1, 321))
model_path = Path("./your_model/model_cuda.pt").resolve()
data_path = Path("./your_images").resolve()
out_path = Path("./your_output").resolve()
classes = ds.DEFAULT_CLASSES

# Detection
model = torch.jit.load(str(model_path))
dataset_format = str(data_path / "{cam_id:s}/{frame:04d}.jpg")
out_path.mkdir(parents=True, exist_ok=True)
detection.run_detection(model, dataset_format, classes, out_path,
                        frames=frames, cam1_name=f"gp{cam1}",
                        cam2_name=f"gp{cam2}", threshold=0.7)
