import os, sys
import csv
from enum import Flag, auto

import scipy
import numpy as np
import torchaudio
import torch
import matplotlib.cm as cm

class Recog:

    def __init__(self, ASTModel, input_tdim, label_path, pth_name="audioset_10_10_0.4593.pth"):
        self.labels, self.ids = self.load_label(label_path)

        ast_mdl = ASTModel(label_dim=527, input_tdim=input_tdim, imagenet_pretrain=False, audioset_pretrain=False)

        # load weights
        self.checkpoint_path = f'{os.environ["TORCH_HOME"]}/{pth_name}'
        print(f'[*INFO] load checkpoint: {self.checkpoint_path}')
        checkpoint = torch.load(self.checkpoint_path)#, map_location='cpu')
        self.audio_model = torch.nn.DataParallel(ast_mdl)#, device_ids=[0])
        self.audio_model.load_state_dict(checkpoint)

        self.audio_model.eval() # set the eval model

    def infer(self, feats_data):
        with torch.no_grad():
            #start = time.time()
            output = self.audio_model.forward(feats_data)
            #end = time.time()
            output = torch.sigmoid(output)
        self.result_output = output.data.cpu().numpy()
        return self.result_output

    def label_indices(self, result_output=None):
        if result_output is None:
            result_output = self.result_output

        return np.argsort(result_output, axis=1)[..., ::-1]

    def load_label(self, label_csv_path):
        with open(label_csv_path, 'r') as f:
            reader = csv.reader(f, delimiter=',')
            lines = list(reader)
        labels = []
        ids = []  # Each label has a unique id such as "/m/068hy"
        for i1 in range(1, len(lines)):
            id = lines[i1][1]
            label = lines[i1][2]
            ids.append(id)
            labels.append(label)
        return np.array(labels), np.array(ids)

    @classmethod
    def waveplot(cls, plt, librosa, y, sr, ax=None, w=16, h=4):
        if type(y) == torch.Tensor:
            y = y.to('cpu').detach().numpy().copy()

        if ax is None:
            plt.figure(figsize=(w, h))
            librosa.display.waveplot(y=y, sr=sr)
        else:
            librosa.display.waveplot(y=y, sr=sr, ax=ax)

    @classmethod
    def specshow(cls, plt, librosa, fbank, sr, hop_length, cb=True, ax=None, title="", w=16, h=4):
        # https://qiita.com/ykatsu111/items/c69122fc3e3b77ec50a8

        if type(fbank) == np.ndarray:
            data = fbank
        else:
            data = fbank.transpose(1, 0).to('cpu').detach().numpy().copy()

        if ax is None:
            plt.figure(figsize=(w, h))
            librosa.display.specshow(data=data, sr=sr, hop_length=hop_length, x_axis='time', y_axis='mel')
            plt.colorbar(format='%+2.0f dB')
            plt.title(title)
            plt.tight_layout()
        else:
            fig = plt
            img = librosa.display.specshow(data=data, sr=sr, hop_length=hop_length, x_axis='time', y_axis='mel', ax=ax)
            if cb:
                cb = fig.colorbar(img, format='%+2.0f dB')
            fig.tight_layout()
            return cb

    @classmethod
    def classifyshow(cls, ontology, abst_scores_series, xstep=1, ax=None, title="", w=16, h=4):
        # https://www.wizard-notes.com/entry/music-analysis/timelinechart-with-matplotlib

        labels = []
        for segment, abst_scores in abst_scores_series.items():
            if type(abst_scores) is tuple:
                abst_scores = abst_scores[0]

            for i, ident in enumerate(reversed(sorted(abst_scores.keys(), key=lambda i: ontology.to_name(i)))):
                score = abst_scores[ident]
                ax.broken_barh([segment], (i, 1), facecolors=cm.jet(score/100))
                #print(segment, (i, i+1), ontology.to_name(ident))

            if len(labels) < len(abst_scores.keys()):
                labels = list(reversed(sorted(map(lambda i: ontology.to_name(i), abst_scores.keys()))))

        ax.set_title(title)

        ax.set_xlabel('Time')
        start, end = ax.get_xlim()
        ax.xaxis.set_ticks(np.arange(start, end, xstep))

        ax.set_yticks(np.arange(0, len(labels))+0.5)
        ax.set_yticklabels(labels)


    @classmethod
    def fbank(cls, y, sr, target_length, mel_bins=128, frame_shift=10, repeat=False):
        if type(y) == np.ndarray:
            waveform = torch.from_numpy(y.astype(np.float32)).clone().cpu()
        else:
            waveform = y

        fbank = torchaudio.compliance.kaldi.fbank(
                waveform, htk_compat=True, sample_frequency=sr, use_energy=False,
                window_type='hanning', num_mel_bins=mel_bins, dither=0.0, frame_shift=frame_shift)
        #print(f"fbank Shape: {fbank.shape}")

        if target_length != 0:
            n_frames = fbank.shape[0]
            p = target_length - n_frames
            if p > 0:
                # Zero padding
                if not repeat:
                    m = torch.nn.ZeroPad2d((0, 0, 0, p))
                    fbank = m(fbank)
                else:
                    n = target_length//n_frames
                    m = target_length%n_frames
                    fbank = torch.concat([fbank.repeat(n, 1), fbank[:m, ...]], axis=0)
            elif p < 0:
                    fbank = fbank[0:target_length, :]

        return (fbank - (-4.2677393)) / (4.5689974 * 2)


    def abst_infer(self, wav, sr, ontology, interests, target_length=1024, mel_bins=128, frame_shift=10, repeat=False):

        fbank_orig = Recog.fbank(wav, sr, target_length, mel_bins=mel_bins, frame_shift=frame_shift, repeat=repeat)

        tensor = fbank_orig.expand(1, target_length, mel_bins)           # reshape the feature
        result = self.infer(tensor)
        sorted_indices = self.label_indices(result)

        total = result[0,:].sum()


        conc_scores = {self.ids[si]: result[0, si]/total*100 for si in sorted_indices[0, :]}
        abst_scores = ontology.abst_scores(conc_scores, interests)

        return abst_scores, conc_scores, result

    # search cache. count can be negative value
    def cache(self, series, start, delta, count):

        sign = np.sign(count)

        result = {}
        for i in range(abs(count)):
            cur = start + delta * i*sign
            k   = (cur, delta)
            try:
                result[k] = series[k]
            except KeyError:
                raise NotImplementedError()
                #series[k] =
        return result

    @classmethod
    def is_music(cls, infresult, music_thres, hs_thres, music_ids, hs_id):

        music = any(map(lambda ident: infresult[ident] >= music_thres, music_ids))
        human_sound = infresult[hs_id] >= hs_thres

        if music:
            if human_sound:
                return State.Talking
            else:
                return State.Music
        else:
            return State.Other

    def estim_segment(self, onto, series, start, delta, count, music_thres = 35, hs_thres = 35):

        music_ids = list(map(lambda o: o["id"], onto["^(Music|Singing)$"]))
        hs_id = onto["^Human sounds$"][0]["id"]

        segment = Recog.cache(self, series, start, delta, count)
        prev_state = cur_state = None
        cur_interval = None
        result = {}

        # combine intervals
        for interval in sorted(segment.keys(), key=lambda i: i[0]): # sort by starttime
            abst_result = segment[interval][0]
            cur_state = Recog.is_music(abst_result, music_thres, hs_thres, music_ids, hs_id)

            if cur_state != prev_state:
                if cur_interval is not None:
                    result[tuple(cur_interval)] = prev_state

                prev_state = cur_state
                cur_interval = list(interval)
            else:
                cur_interval[1] += interval[1]

        result[tuple(cur_interval)] = cur_state

        return result

    #                                                             length of BGM after talking ended
    def judge_segment(self, onto, series, start, delta, duration, aft_thres=3):
        if duration > 5:
            raise ValueError(f"duration({duration}) must be <= 5")

        concrete_result = Recog.estim_segment(self, onto, series, start, delta, int(np.ceil(duration/delta)))
        print(concrete_result)

        # judge
        prev_state = cur_state = None
        prev_interval = None
        judgement = State.Music | State.InProgress
        event_time = start
        for cur_interval in sorted(concrete_result.keys(), key=lambda i: i[0]): # sort by starttime

            cur_state = concrete_result[cur_interval]
            cur_istart, cur_idurat = cur_interval

            if cur_state != State.Music and judgement == State.Music | State.InProgress:
                judgement = State.Other

            #print(prev_state, cur_state)

            if prev_state is not None:
                prev_istart, prev_idurat = prev_interval

                if cur_state != prev_state: # State change
                    if cur_state == State.Music: # into music

                        if prev_state == State.Talking and cur_idurat < aft_thres: # is Talking
                            judgement = State.Talking
                        else: # start Music
                            judgement = State.Music | State.Start
                            event_time = cur_istart

                    elif prev_state == State.Music: # end music
                        judgement = State.Music | State.End
                        event_time = cur_istart

                    else:
                        judgement = State.Other | State.InProgress

            prev_state = cur_state
            prev_interval = cur_interval

        return judgement, event_time




class State(Flag):
    Music = auto()
    Talking = auto()
    Other = auto()

    Start = auto()
    InProgress = auto()
    End = auto()
