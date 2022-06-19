"""Script to write the currently ported config in a human-readable form."""
from utils.configs import old_ported_config
from utils.datasets import HGS

cfg = old_ported_config(HGS.train)
with open("current_config.yaml", "w") as f:
  f.write(cfg.dump())
