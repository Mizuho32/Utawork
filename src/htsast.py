import os, sys, time
import csv, re
from enum import Flag, auto
import functools
import pathlib, datetime

import scipy
import numpy as np
import torchaudio
import torch
import matplotlib.cm as cm
import librosa
import yaml
import pickle

class HTSAST:
    def __init__(self, model_path, config, device="cuda"):
        self.device = torch.device(device)

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
        ckpt = torch.load(model_path, map_location=self.device)
        temp_ckpt = {}
        for key in ckpt["state_dict"]:
            temp_ckpt[key[10:]] = ckpt['state_dict'][key]
        self.sed_model.load_state_dict(temp_ckpt)
        self.sed_model.to(self.device)
        self.sed_model.eval()


    def predict(self, waveform):

        if audiofile:
            waveform, sr = librosa.load(audiofile, sr=32000, offset = offset, duration = duration)

		with torch.no_grad():
			x = torch.from_numpy(waveform).float().to(self.device)
			output_dict = self.sed_model(x[None, :], None, True)
			return output_dict

    def getlabel(self, output_dict):
        pred = output_dict['clipwise_output']
        pred_post = pred[0].detach().cpu().numpy()
        pred_label = np.argmax(pred_post)
        pred_prob = np.max(pred_post)
        return pred_label, pred_prob
