import os, sys
import csv, re
from enum import Flag, auto
import functools

import scipy
import numpy as np
import torchaudio
import torch
import matplotlib.cm as cm

from . import utils

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
    def state_show(cls, labels, state_series, xstep=1, ax=None, title="", w=16, h=4):

        label2yval = {state.value: i for i, state in enumerate(reversed(sorted(labels, key=lambda s: s.name)))}
        colors = np.linspace(0, 100, len(labels))
        #print(label2yval)

        for segment, states in state_series.items():
            for state in states:
                yval = label2yval[state.value]
                #print(segment, state, yval)
                ax.broken_barh([segment], (yval, 1), facecolors=cm.jet(colors[yval]/100))

        ax.set_title(title)

        ax.set_xlabel('Time')
        start, end = ax.get_xlim()
        ax.xaxis.set_ticks(np.arange(start, end, xstep))

        ax.set_yticks(np.arange(0, len(labels))+0.5)
        ax.set_yticklabels(list(reversed(sorted(map(lambda l: l.name, labels)))))

    @classmethod
    def detect_show(cls, detect_series, xstep=1, ax=None, title="", w=16, h=4):

        labels = [State.Music|State.Start, State.Music|State.InProgress, State.Music|State.End, State.Talking, State.Other]

        print(labels)

        sorted_labels = list(reversed(sorted(labels, key=lambda s: s.value)))
        label2yval = {state.value: i for i, state in enumerate(sorted_labels)}
        colors = np.linspace(0, 100, len(labels))

        for event_time, state in detect_series.items():
            yval = label2yval[state.value]
            ax.broken_barh([(event_time, 0.5)], (yval, 1), facecolors=cm.jet(colors[yval]/100))

        ax.set_title(title)

        ax.set_xlabel('Time')
        start, end = ax.get_xlim()
        ax.xaxis.set_ticks(np.arange(start, end, xstep))

        ax.set_yticks(np.arange(0, len(labels))+0.5)
        ax.set_yticklabels(list(map(lambda l: str(l) ,sorted_labels)))



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

        #print(wav.shape, sr, target_length, mel_bins, frame_shift, repeat)
        fbank_orig = Recog.fbank(wav, sr, target_length, mel_bins=mel_bins, frame_shift=frame_shift, repeat=repeat)

        tensor = fbank_orig.expand(1, target_length, mel_bins)           # reshape the feature
        result = self.infer(tensor)
        sorted_indices = self.label_indices(result)

        total = result[0,:].sum()


        conc_scores = {self.ids[si]: result[0, si]/total*100 for si in sorted_indices[0, :]}
        abst_scores = ontology.abst_scores(conc_scores, interests)

        return abst_scores, conc_scores, result

    # search cache. count can be negative value
    def cache(self, series, start, delta, count, wav, sr, ontology, interests):

        sign = np.sign(count)

        result = {}
        for i in range(abs(count)):
            cur = start + delta * i*sign
            k   = (cur, delta)
            try:
                result[k] = series[k]
            except KeyError:
                wav_cut = wav[:, int(sr*cur):int(sr*(cur+delta))]
                if wav_cut.shape[1] > 0:
                    series[k] = Recog.abst_infer(self, wav_cut, sr, ontology, interests)
                    result[k] = series[k]

        return result

    @classmethod
    def categorize(cls, infresult, music_thres, hs_thres, music_ids, hs_id):

        music = any(map(lambda ident: infresult[ident] >= music_thres, music_ids))
        human_sound = infresult[hs_id] >= hs_thres
        states = []

        if human_sound:
            states.append( State.Talking )
        if music:
            states.append( State.Music )
        if not human_sound and not music:
            states.append( State.Other )

        return states

    # do inference and combine the same value state sequence
    def estim_segment(self, onto, series, start, delta, count, wav, sr, ontology, interests, music_thres = 35, hs_thres = 35):

        music_ids = list(map(lambda o: o["id"], onto["^(Music|Singing)$"]))
        hs_id = onto["^Human sounds$"][0]["id"]

        labels = [State.Music, State.Talking, State.Other]

        segment = Recog.cache(self, series, start, delta, count, wav, sr, ontology, interests)
        bag = {label: {"prev_state": False, "cur_state": False, "cur_interval": None, "result": []} for label in labels}

        # combine intervals
        for interval in sorted(segment.keys(), key=lambda i: i[0]): # sort by starttime

            abst_result = segment[interval][0] # (abst, conc, rawdata)
            cur_states = Recog.categorize(abst_result, music_thres, hs_thres, music_ids, hs_id)

            for label in labels:
                bag[label]["cur_state"] = label in cur_states
                cur_state, prev_state = bag[label]["cur_state"], bag[label]["prev_state"]
                cur_interval = bag[label]["cur_interval"]

                if cur_state != prev_state:
                    if cur_state:  # if label is true, register cur_interval
                        bag[label]["cur_interval"] = list(interval)
                    else:
                        bag[label]["result"].append( tuple(cur_interval) )
                        bag[label]["cur_interval"] = None
                else:
                    if cur_state:
                        bag[label]["cur_interval"][1] += interval[1] # extend duration

                bag[label]["prev_state"] = cur_state

        for label in labels:
            ci = bag[label]["cur_interval"]
            if ci is not None:
                bag[label]["result"].append(tuple(ci))


        result = {}
        for label, v in bag.items():
            for itv in v["result"]:
                try:
                    result[itv].append(label)
                except KeyError:
                    result[itv] = [label]

        return result


    # aft_thres: length of BGM after talking ended
    def judge_segment(self, onto, series, start, delta, duration, wav, sr, ontology, interests, aft_thres=3):
        if duration > 5:
            raise ValueError(f"duration({duration}) must be <= 5")

        concrete_result = Recog.estim_segment(self, onto, series, start, delta, int(np.ceil(duration/delta)), wav, sr, ontology, interests)
        print(concrete_result,"\n")

        # judge
        prev_states = cur_states = [None]
        prev_interval = None
        judgement = State.Music | State.InProgress
        event_time = start

        union = lambda states: functools.reduce( lambda acc,x: acc|x, states, states[0])

        for cur_interval, cur_states in utils.each_state(concrete_result): # time order

            cur_istart, cur_idurat = cur_interval

            if not State.Music in cur_states and judgement == (State.Music | State.InProgress):
                judgement = State.Other

            #print(prev_states, cur_states)

            if prev_states != [None]:
                prev_istart, prev_idurat = prev_interval

                if union(cur_states) != union(prev_states): # State change
                    if State.Music in cur_states: # into music

                        if State.Talking in prev_states and cur_idurat < aft_thres: # is Talking
                            judgement = State.Talking
                        else: # start Music
                            judgement = State.Music | State.Start
                            event_time = cur_istart

                    elif State.Music in prev_states: # end music
                        judgement = State.Music | State.End
                        event_time = cur_istart

                    else:
                        judgement = State.Other | State.InProgress

            prev_states = cur_states
            prev_interval = cur_interval

        return judgement, event_time, concrete_result


    def detect_music(self, onto, series, start, delta, duration, wav, sr, ontology, interests,
            min_interval=5):

        result = {}
        concrete_result = {}
        cur_time = start

        for i in range(10):
            state, event_time, c_result = Recog.judge_segment(self, onto, series, cur_time, delta, duration, wav, sr, ontology, interests)
            result[event_time] = state
            concrete_result = {**c_result, **concrete_result}
            cur_time += min_interval

        return result, concrete_result







class State(Flag):
    Music = auto()
    Talking = auto()
    Other = auto()

    Start = auto()
    InProgress = auto()
    End = auto()
