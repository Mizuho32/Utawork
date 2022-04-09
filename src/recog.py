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
    def waveplot(cls, plt, librosa, y, sr, offset=0.0, ax=None, w=16, h=4):
        if type(y) == torch.Tensor:
            y = y.to('cpu').detach().numpy().copy()

        if ax is None:
            plt.figure(figsize=(w, h))
            librosa.display.waveplot(y=y, sr=sr, offset=offset)
        else:
            librosa.display.waveplot(y=y, sr=sr, ax=ax, offset=offset)

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

                ax.text(segment[0], yval+0.4, "<", color="white")
                ax.text(sum(segment)-0.5, yval+0.4, ">", color="white")

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

    # FIXME: compare sesgment? for the case of realtively high score, thres fixneeded
    # do inference and combine the same value state sequence
    def estim_segment(self, onto, series, start, delta, count, wav, sr, ontology, interests, music_thres = 30, hs_thres = 30):

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
        #print(concrete_result)

        # judge
        prev_states = cur_states = [None]
        prev_interval = None
        judgement = State.Music | State.InProgress
        event_time = start
        judges = {}

        union = lambda states: functools.reduce( lambda acc,x: acc|x, states, states[0])
        scores = {st: 0 for st in [State.Music, State.Other, State.Talking]}

        for cur_interval, cur_states in utils.each_state(concrete_result): # time order

            cur_istart, cur_idurat = cur_interval


            for cur_state in cur_states:
                if cur_state in scores:
                    scores[cur_state] += cur_idurat

            if prev_states != [None]:
                prev_istart, prev_idurat = prev_interval

                if union(cur_states) != union(prev_states): # State change
                    if State.Music in cur_states and not State.Music in prev_states: # into music
                        judgement = State.Music | State.Start
                        event_time = cur_istart
                        judges[event_time] = judgement

                    elif State.Music in prev_states and not State.Music in cur_states: # end music
                        judgement = State.Music | State.End
                        event_time = cur_istart
                        judges[event_time] = judgement

            prev_states = cur_states
            prev_interval = cur_interval

        if not judges:
            judgement, _ = max(scores.items(), key=lambda st_score: st_score[1])
            if judgement == State.Music:
                judges[start] = State.Music|State.InProgress
            else:
                judges[start] = judgement

        return judges, concrete_result

    @classmethod
    def judges_denoised(cls, judges, concrete_result, thres):

        denoised = {k: v for k,v in judges.items()}
        musics_sorted = filter(lambda t_s: State.Music in t_s[1], sorted(judges.items(), key=lambda t_s: t_s[0]))
        cons = utils.each_cons(list(musics_sorted), 2)

        for prev, cur in cons:
            prev_event_time, prev_state = prev
            cur_event_time, cur_state = cur

            # remove very short (music or non music)
            if cur_event_time - prev_event_time <= thres:
                if State.End in prev_state and State.Start in cur_state or \
                   State.Start in prev_state and State.End  in cur_state:
                    denoised.pop(prev_event_time)
                    denoised.pop(cur_event_time)

            if not denoised:
                # calc biggest
                b = {}
                for itv, states in concrete_result.items():
                    for state in states:
                        if state in b:
                            b[state][1] += itv[1]
                            if b[state][0] > itv[0]:
                                b[state][0] = itv[0]
                        else:
                            b[state] = list(itv)

                # sort by state who has biggest time duration
                biggest, itv = sorted(b.items(), key=lambda s_itv: s_itv[1][1] )[-1]

                if biggest == State.Music:
                    biggest = biggest|State.InProgress
                denoised[itv[0]] = biggest

        return denoised


    def detect_music(self, onto, series, start, delta, duration, wav, sr, ontology, interests,
            music_length=4*60, music_check_len=20, thres=1.0,
            min_interval=5, big_interval=15):

        result, result_d = {}, {}
        concrete_result = {}
        cur_time = start
        prev_judge = None
        prev_c_results = None
        interval_plan = []
        detect_back_target = None

        def add_(result, judges):
            for event_time, state in judges.items():
                result[event_time] = state

        def last_cur_time(prev_c_results): # FIXME: LINQ
            min_times = map(lambda cr: min(map(lambda itv:itv[0], cr.keys())), prev_c_results)
            return max(min_times)

        for i in range(10):
            try:
                judges, c_result = Recog.judge_segment(self, onto, series, cur_time, delta, duration, wav, sr, ontology, interests)
            except IndexError:
                break

            print(judges)
            judges_d = Recog.judges_denoised(judges, c_result, thres)
            cur_judge = judges_d[max(judges_d.keys())]

            judgess, c_results = [judges], [c_result]


            if prev_judge != None:
                if not State.Music in prev_judge and State.Music in cur_judge: # non Music -> Music
                    if State.Start in cur_judge: # music start
                        is_starting, next_cur_time, judgess, c_results = \
                            Recog.is_music_starting(self, series, cur_time, delta, duration, music_check_len, min_interval, wav, sr, ontology, interests, thres=thres)

                        if is_starting:
                            #tmp = Recog.judges_denoised(judgess[-1], c_results[-1], thres)
                            #cur_judge = tmp[max(tmp.keys())]
                            interval_plan = [*Recog.interval_plan(music_length, big_interval, min_interval), next_cur_time - cur_time]
                    else: # next is music InPro or End, without Starting
                        detect_back_target = State.Music|State.Start

                elif State.Music in prev_judge and not State.Music in cur_judge: # Music -> non Music
                    if not State.End in prev_judge: # music end not detected
                        detect_back_target = State.Music|State.End

                if detect_back_target != None:
                    detected_judge, tmp_j, tmp_c = Recog.back_to_change(self, detect_back_target, series, cur_time, delta, duration, last_cur_time(prev_c_results), wav, sr, ontology, interests, thres = thres)
                    judgess, c_results = [*judgess, *tmp_j], [*c_results, *tmp_c]

                    if detected_judge != None:
                        add_(result_d, judges_d)
                        judges_d = detected_judge
                    else:
                        print(f"Failed to find {detect_back_target} (at {cur_time})")

                    detect_back_target = None


            for judges in judgess:
                add_(result, judges)
            for c_result in c_results:
                concrete_result = {**c_result, **concrete_result}
            add_(result_d, judges_d)

            if interval_plan:
                cur_time += interval_plan.pop()
            else:
                cur_time += min_interval

            prev_judge = cur_judge
            prev_c_results = c_results

        return result, result_d, concrete_result

    # mcl: music check length [sec]
    def is_music_starting(self, series, start, delta, duration, mcl, interval, wav, sr, ontology, interests, thres = 1.0):

        count = int(mcl // interval)
        c_results = []
        judgess = []
        cur_time = start

        music_starting = True

        for i in range(count):
            judges, c_result = Recog.judge_segment(self, ontology, series, cur_time, delta, duration, wav, sr, ontology, interests)

            c_results.append(c_result)
            judgess  .append(judges)

            # denoise and check music ends?
            judges_d = Recog.judges_denoised(judges, c_result, thres)
            if any(map(lambda etime_st: State.Music|State.End == etime_st[1], judges_d.items())):
                music_starting = False

            cur_time += interval

        last_time = min(map(lambda start_itv: start_itv[0], c_results[-1].keys())) # start time of last segment
        return music_starting, last_time, judgess, c_results

    # start: future,  end: past
    def back_to_change(self, target, series, start, delta, duration, end, wav, sr, ontology, interests, thres = 1.0):
        length = start - (end+duration)
        count = int(length // duration)

        # overwrapping intervals
        itvs = [(start-duration*(i+2) -delta, duration +delta) for i in range(count-2)] # middle itvs
        itvs.insert(0, (start-duration -delta, duration +2*delta))
        rest_delta = length - duration*count  +delta
        itvs.append( tuple(map(lambda i: utils.round(i, 1), (start-length -delta, duration+rest_delta))) )

        c_results = []
        judgess = []
        print(itvs)

        # search even -> odd, 1delta overwrap
        for j in range(2):
            for i in map(lambda i: i*2, range(int(len(itvs)/2+1))):
                try:
                    time, duration = itvs[j+i]
                    judges, c_result = Recog.judge_segment(self, ontology, series, time, delta, duration, wav, sr, ontology, interests)
                    c_results.append(c_result)
                    judgess  .append(judges)

                    judges_d = Recog.judges_denoised(judges, c_result, thres)
                    if any(map(lambda etime_st: target == etime_st[1], judges_d.items())):
                        return judges_d, judgess, c_results

                except IndexError:
                    break

        return None, judgess, c_results



    @classmethod
    def interval_plan(cls, music_len, big_interval, min_interval):
        big_count = music_len // big_interval
        min_count = (music_len-big_interval*big_count) // min_interval

        return [*[min_interval]*min_count, *[big_interval]*big_count]















class State(Flag):
    Music = auto()
    Talking = auto()
    Other = auto()

    Start = auto()
    InProgress = auto()
    End = auto()
