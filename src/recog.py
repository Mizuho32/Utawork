import os
import sys

import scipy
import numpy as np
import torchaudio
import torch

class Recog:

    def __init__(self):
        print()

    @classmethod
    def waveplot(cls, plt, librosa, y, sr, w=16, h=4):
        plt.figure(figsize=(w, h))
        librosa.display.waveplot(y=y, sr=sr)

    @classmethod
    def specshow(cls, plt, librosa, fbank, sr, hop_length, title="", w=16, h=4):
        plt.figure(figsize=(w, h))

        if type(fbank) == np.ndarray:
            data = fbank
        else:
            data = fbank.transpose(1, 0).to('cpu').detach().numpy().copy()

        librosa.display.specshow(data=data, sr=sr, hop_length=hop_length, x_axis='time', y_axis='mel')
        plt.colorbar(format='%+2.0f dB')

        plt.title(title)
        plt.tight_layout()

    @classmethod
    def fbank(cls, y, sr, target_length, mel_bins=128, frame_shift=10):
        if type(y) == np.ndarray:
            waveform = torch.from_numpy(y.astype(np.float32)).clone().cpu()
        else:
            waveform = y

        fbank = torchaudio.compliance.kaldi.fbank(
                waveform, htk_compat=True, sample_frequency=sr, use_energy=False,
                window_type='hanning', num_mel_bins=mel_bins, dither=0.0, frame_shift=frame_shift)
        print(f"fbank Shape: {fbank.shape}")

        # Zero padding
        n_frames = fbank.shape[0]
        p = target_length - n_frames
        if p > 0:
            m = torch.nn.ZeroPad2d((0, 0, 0, p))
            fbank = m(fbank)
        elif p < 0:
                fbank = fbank[0:target_length, :]

        return (fbank - (-4.2677393)) / (4.5689974 * 2)
