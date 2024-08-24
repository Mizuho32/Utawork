import torch
import numpy as np
import librosa
from zsass.models.htsat import HTSAT_Swin_Transformer

from typing import Dict, List, Optional, Tuple, Callable
from . import utils, audioset

class AudioClassifier:
    def __init__(self, model_path, config, interests: List[dict], ontology: utils.Ontology, audioset: audioset.AudioSet):
        super().__init__()

        self.device = torch.device('cuda')
        self.sed_model = HTSAT_Swin_Transformer(
            spec_size=config.htsat_spec_size,
            patch_size=config.htsat_patch_size,
            in_chans=1,
            num_classes=config.classes_num,
            window_size=config.htsat_window_size,
            config = config,
            depths = config.htsat_depth,
            embed_dim = config.htsat_dim,
            patch_stride=config.htsat_stride,
            num_heads=config.htsat_num_head
        )
        ckpt = torch.load(model_path, map_location="cuda")
        temp_ckpt = {}
        for key in ckpt["state_dict"]:
            temp_ckpt[key[10:]] = ckpt['state_dict'][key]
        self.sed_model.load_state_dict(temp_ckpt)
        self.sed_model.to(self.device)
        self.sed_model.eval()

        self.abst_concidx = ontology.absts_conc_indices(interests, audioset)
        self.ontology = ontology


    def predict(self, audiofile, sr = 32000, offset = None, duration = None):
        waveform, sr = librosa.load(audiofile, sr=sr, offset = offset, duration = duration)
        return self.infer(waveform), waveform, sr
            
    def infer(self, waveform):
        with torch.no_grad():
            x = torch.from_numpy(waveform).float().to(self.device)
            output_dict = self.sed_model(x[None, :], None, True)
            return output_dict

    def abst_tensor(self, result_tensor: torch.Tensor, simplifi_interval=32) -> torch.Tensor:

        # reduce by max
        abst_tensor = []
        for abst_id in sorted(self.abst_concidx.keys(), key=lambda i: self.ontology.to_name(i)):
            conc_idxs = self.abst_concidx[abst_id]
            abst_tensor.append(result_tensor[:, conc_idxs].max(dim=1).values)

        return torch.vstack(abst_tensor).transpose(1, 0)[::simplifi_interval, :]
    
    @classmethod # -> [ [start, end], ...]
    def music_intervals(cls, abst_tensor: torch.Tensor, offset: float, duration: float, thres: Optional[float], predicate: Callable[[torch.Tensor], torch.Tensor] = None, target_index=3) -> np.ndarray:
        resolution, _ = abst_tensor.shape
        def to_time(start, end):
            return np.array([start.numpy(), end])/resolution*duration + offset

        if predicate is None:
            filtered = abst_tensor[:, target_index] >= thres
        else:
            filtered = predicate(abst_tensor)

        indices = torch.nonzero(filtered)[:, 0]
        idx_len = len(indices)
        indices = list(indices) + [None]

        start = indices[0]
        itvs = [np.empty((0, 2))]

        if start == None:
            idx_len = 0

        for idx in range(idx_len):
            pre = indices[idx]
            nxt = indices[idx+1]

            if nxt == None:
                itvs.append( to_time(start, pre+1) )
            elif nxt - pre != 1:
                itvs.append( to_time(start, pre+1) )
                start = nxt

        return np.vstack(itvs)




    def getlabel(self, output_dict):
        pred = output_dict['clipwise_output']
        pred_post = pred[0].detach().cpu().numpy()
        pred_label = np.argmax(pred_post)
        pred_prob = np.max(pred_post)
        return pred_label, pred_prob