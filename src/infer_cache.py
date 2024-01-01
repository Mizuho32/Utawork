import numpy as np
import torch

class InferCache:
    def __init__(self, index: int, offset: float, duration: float, abst_tensor: torch.Tensor, music_intervals: np.ndarray):
        self.index = index
        self.offset = offset
        self.duration = duration
        self.abst_tensor = abst_tensor
        self.music_intervals = music_intervals