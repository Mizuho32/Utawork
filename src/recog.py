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

from . import utils

class Recog:

    def __init__(self, ASTModel, input_tdim, label_path, pth_name="audioset_10_10_0.4593.pth", model_sr=16000):
        self.labels, self.ids = self.load_label(label_path)
        self.wav_offset = 0
        self.model_sr = model_sr

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
    def waveplot(cls, plt, librosa, y, sr, offset=0.0, max_sr=100, ax=None, w=16, h=4):

        if max_sr > 100:
            max_sr = 100

        if type(y) == torch.Tensor:
            y = y.to('cpu').detach().numpy().copy()

        if y.shape[0]==1: #mono
            y = y.reshape(y.shape[-1])

        if ax is None:
            plt.figure(figsize=(w, h))
            librosa.display.waveplot(y=y, sr=sr, offset=offset, max_sr=max_sr)
        else:
            librosa.display.waveplot(y=y, sr=sr, ax=ax, offset=offset, max_sr=max_sr)

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

        itvs = {}
        scores = {}
        for itv in sorted(abst_scores_series.keys(), key=lambda itv: itv[0]):

            abst_scores = abst_scores_series[itv]
            if type(abst_scores) is tuple:
                abst_scores = abst_scores[0]

            for ident, score in abst_scores.items():
                try:
                    itvs[ident].append(itv)
                except KeyError:
                    itvs[ident] = [itv]
                try:
                    scores[ident].append(score)
                except KeyError:
                    scores[ident] = [score]

        for i, ident in enumerate(reversed(sorted(itvs.keys(), key=lambda i: ontology.to_name(i)))):
            colors = list(map(lambda score: cm.jet(score/100), scores[ident]))
            ax.broken_barh(itvs[ident], (i, 1), facecolors=colors)

        labels = list(reversed(sorted(map(lambda i: ontology.to_name(i), itvs.keys()))))

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
        if int(sr) != int(self.model_sr):
            wav = utils.resample(wav, sr, self.model_sr)
            sr = self.model_sr

        fbank_orig = Recog.fbank(wav, sr, target_length, mel_bins=mel_bins, frame_shift=frame_shift, repeat=repeat)

        tensor = fbank_orig.expand(1, target_length, mel_bins)           # reshape the feature
        result = self.infer(tensor)
        sorted_indices = self.label_indices(result)

        total = result[0,:].sum()


        conc_scores = {self.ids[si]: result[0, si]/total*100 for si in sorted_indices[0, :]}
        abst_scores = ontology.abst_scores(conc_scores, interests)

        return abst_scores, conc_scores, result

    def slice_wav(self, wav, sr, start, end):
        slice_start = int(sr*(start - self.wav_offset))
        slice_end   = int(sr*(end   - self.wav_offset))

        if slice_start < 0 or slice_end > wav.shape[-1]:
            raise IndexError(f"Invalid slice {slice_start}:{slice_end} for {wav.shape}")

        return wav[..., slice_start:slice_end]

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
                wav_cut = Recog.slice_wav(self, wav, sr, cur, cur+delta)
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
        musics_sorted = filter(lambda t_s: State.Music in t_s[1], sorted(judges.items(), key=lambda t_s: t_s[0])) # filter Music States and sort by time #FIXME: LINQ
        cons = utils.each_cons(list(musics_sorted), 2)

        #print(cons)
        for prev, cur in cons:
            prev_event_time, prev_state = prev
            cur_event_time, cur_state = cur

            # remove very short (music or non music)
            if cur_event_time - prev_event_time <= thres:
                if State.End in prev_state and State.Start in cur_state or \
                   State.Start in prev_state and State.End  in cur_state:
                    #print(f"pop {prev_event_time}, {cur_event_time}")
                    try:
                        denoised.pop(prev_event_time)
                        denoised.pop(cur_event_time)
                        denoised[prev_event_time] = State.Music|State.InProgress # FIXME: cases not only for music
                    except KeyError: # already deleted
                        pass

        if not denoised:
            # calc biggest
            b = {}
            times = []
            for itv, states in concrete_result.items():
                times = [*times, itv[0], sum(itv)]
                for state in states:
                    if state in b:
                        b[state] += itv[1]
                    else:
                        b[state] = itv[1]

            # filter, sort by state who has biggests time duration
            leng = max(times)-min(times)
            #FIXME: LINQ, 0.5 thres
            biggests = list(map(lambda s_dur: s_dur[0],
                sorted(filter(lambda s_dur: s_dur[1]/leng > 0.5, b.items()), key=lambda s_dur: s_dur[1]) ))
            if times and biggests:
                if State.Music in biggests:
                    biggest = State.Music|State.InProgress
                else:
                    biggest = biggests[-1]
                denoised[min(times)] = biggest

        return denoised

    @classmethod
    def last_cur_time(cls, prev_c_results): # FIXME: LINQ
        min_times = map(lambda cr: min(map(lambda itv:itv[0], cr.keys())), prev_c_results)
        return max(min_times)


    def detect_music(self, series, start, delta, duration, wav_offset, wav, sr, ontology, interests,
            music_length=4*60, music_check_len=20, thres=1.0,
            min_interval=5, big_interval=15, stop=np.infty,

            cur_time = None,
            prev_judge = None, prev_c_results= None, prev_judges_d = None,
            prev_abs_mean = 0,
            interval_plan = [],
            detect_back_target = None, entire_abs_mean = 0 ):

        self.wav_offset = wav_offset
        entire_abs_mean = entire_abs_mean or np.abs(wav).mean()

        result = {}
        result_d = {}
        concrete_result = {}


        state_vars = [
            "cur_time",		"prev_judge",    "prev_c_results",	"prev_abs_mean", "prev_judges_d",
            "interval_plan","detect_back_target"]

        cur_time = cur_time or start

        def add_(result, judges):
            for event_time, state in judges.items():
                result[event_time] = state

        wav_len = wav.shape[-1]

        while cur_time < stop and sr*(cur_time+duration - wav_offset) < wav_len:

            # do inference
            try:
                judges, c_result = Recog.judge_segment(self, ontology, series, cur_time, delta, duration, wav, sr, ontology, interests)
            except IndexError as ex:
                print(ex)
                raise ex
                break
            cur_abs_mean = np.abs(Recog.slice_wav(self, wav, sr, cur_time, cur_time+duration)).mean()


            utils.print_judges(judges)
            # denoise inference
            judges_d = Recog.judges_denoised(judges, c_result, thres)
            cur_judge = judges_d[max(judges_d.keys())] # get most recent State

            judgess, c_results, judgess_d = [judges], [c_result], [judges_d]

            # detect chagnes
            if prev_judge != None:
                label, detect_back_target = transition(prev_judge, cur_judge)

                # ! Music -> Music
                if Label.Music_Start in label or Label.Music_Already_Start in label: # music start or InPro
                    is_starting, next_cur_time, judgess, c_results = \
                        Recog.is_music_starting(self, series, cur_time, delta, duration, music_check_len, min_interval, wav, sr, ontology, interests, thres=thres)
                    if is_starting:
                        interval_plan = [*Recog.interval_plan(music_length, big_interval, min_interval), next_cur_time - cur_time]
                #elif Music_End_withno_Start in label:

                # Music -> ! Music
                #elif Music_Already_End in label:

                # Music -> Music
                #elif Music_withno_Start in label: # music not start but music (END->InPro)

                elif Label.Music_to_Music in label: # InProgress but
                    # music looks changing? e.g. BGM -> singing and interval plan in progress
                    # FIXME: very naive judgement
                    #if (prev_abs_mean > entire_abs_mean) != (cur_abs_mean > entire_abs_mean) and interval_plan:
                    if interval_plan:
                        #print(f"p,c,e {prev_abs_mean}, {cur_abs_mean}, {entire_abs_mean}")
                        if (prev_abs_mean < entire_abs_mean) and (cur_abs_mean > entire_abs_mean):
                            detect_back_target = State.Music|State.Start
                        elif (prev_abs_mean > entire_abs_mean) and (cur_abs_mean < entire_abs_mean):
                            detect_back_target = State.Music|State.End

                #elif Music_Start_withno_End in label: # Not End but Start


                if detect_back_target != None:
                    print(f"detect_back {detect_back_target}")
                    detected_judge, d_js, tmp_j, tmp_c = Recog.back_to_change(self, prev_judges_d, detect_back_target, series, cur_time, delta, duration, Recog.last_cur_time(prev_c_results), wav, sr, ontology, interests, thres = thres)
                    # FIXME?: should expire old judges?
                    judgess, c_results, judgess_d = [*judgess, *tmp_j], [*c_results, *tmp_c], [*judgess_d, *d_js]
                    if detected_judge == None:
                        print(f"Failed to find {detect_back_target} (at {cur_time})")

                    # FIXME? only for Music END
                    if detect_back_target == State.Music|State.End and detected_judge != None:
                        interval_plan = []

                    detect_back_target = None

            #print(interval_plan)
            for judges in judgess:
                add_(result, judges)
            for c_result in c_results:
                concrete_result = {**c_result, **concrete_result}
            for judges_d_ in judgess_d:
                add_(result_d, judges_d_)

            if interval_plan:
                cur_time += interval_plan.pop()
            else:
                cur_time += min_interval

            prev_judge = cur_judge
            prev_c_results = c_results
            prev_abs_mean = cur_abs_mean
            prev_judges_d = judges_d

        return result, result_d, concrete_result, utils.vars_get(vars(), state_vars)

    # mcl: music check length [sec]
    def is_music_starting(self, series, start, delta, duration, mcl, interval, wav, sr, ontology, interests, thres = 1.0):

        count = int(mcl // interval)
        c_results = []
        judgess = []
        cur_time = start

        music_starting = True

        for i in range(count):
            try:
                judges, c_result = Recog.judge_segment(self, ontology, series, cur_time, delta, duration, wav, sr, ontology, interests)
            except IndexError as ex:
                break

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
    def back_to_change(self, prev_judges_d, target, series, start, delta, duration, end, wav, sr, ontology, interests, thres = 1.0):
        length = start - (end+duration)
        count = int(length // duration)

        # overwrapping intervals
        itvs = [(start-duration*(i+2) -delta, duration +delta) for i in range(count-2)] # middle itvs
        itvs.insert(0, (start-duration -delta, duration +2*delta))
        rest_delta = length - duration*count  +delta
        itvs.append( tuple(map(lambda i: utils.round(i, 1), (start-length -delta, duration+rest_delta))) )

        c_results = []
        judgess = []
        judgess_d = []
        #print("back: ", target)

        # search even -> odd, 1delta overwrap
        for j in range(2):
            for i in map(lambda i: i*2, range(int(len(itvs)/2+1))):
                try:
                    time, duration = itvs[j+i]
                    judges, c_result = Recog.judge_segment(self, ontology, series, time, delta, duration, wav, sr, ontology, interests)
                    c_results.append(c_result)
                    judgess  .append(judges)
                    judgess_d.append( Recog.judges_denoised(judges, c_result, thres) )
                    #print(c_result, judges, judgess_d[-1])

                    # includes target for latest added judges_d? and consistent?
                    if any(map(lambda etime_st: target == etime_st[1], judgess_d[-1].items())) and \
                       Recog.consistent_judge_series([*judgess_d, prev_judges_d]):
                        return judgess_d[-1], judgess_d, judgess, c_results

                except IndexError:
                    break

        return None, [], judgess, c_results

    @classmethod
    def consistent_judge_series(cls, judges_series):

        j_all = {}
        for js in judges_series: # FIXME: LINQ
            for t, j in js.items():
                j_all[t] = j

        cons2 = utils.each_cons(sorted(j_all.items(), key=lambda j: j[0]), 2)
        # transition() -> label, detect_back_target
        return all([ (Label.OK in transition(prev[1], cur[1])[0]) for prev, cur in cons2])


    @classmethod
    def interval_plan(cls, music_len, big_interval, min_interval):
        big_count = int(music_len // big_interval)
        min_count = int((music_len-big_interval*big_count) // min_interval)

        return [*[min_interval]*min_count, *[big_interval]*big_count]


    def detect_music_main(self, filename, save_dir, start, clip_len, delta, duration, ontology, interests, sr, is_mono=False, infer_series = {}, stop_time=np.infty, ignore_steps=[], cache_overwrite=False):

        save_dir = pathlib.Path(save_dir)
        if not save_dir.exists():
            raise FileNotFoundError(f"No such a directory {save_dir}")


        # Load cache
        if not cache_overwrite and (save_dir / "metadata.yaml").exists():

            with open(save_dir / "metadata.yaml", 'r') as file:
                metadata = yaml.safe_load(file)

            i = len(metadata["cache_list"]) - 1 # last data index
            means = list(map(lambda c: c["abs_mean"], metadata["cache_list"]))

            with open(save_dir / metadata["cache_list"][i]["data"], 'rb') as file:
                states = pickle.load(file)["states"]

            wav_offset = Recog.last_cur_time(states["prev_c_results"])
            start = states["cur_time"]
            i += 1

        else:
            wav_offset = start
            means = []
            states = {}
            metadata = {"filename": filename, "delta": delta, "duration": duration, "mono": is_mono,
                        "sr": sr, "cache_list": []}
            i = 0


        while start+clip_len <= stop_time:

            print(f"{i} Start:{start}, offset:{wav_offset}, len:{clip_len}")
            wav, sr = librosa.load(filename, sr=sr, mono=is_mono, offset=wav_offset, duration=clip_len)
            if not sr*(start-wav_offset) < wav.shape[-1]: # empty
                break

            means.append(np.abs(wav).mean())
            entire_abs_mean = np.median(means)


            # Infer
            calc_start = time.time()
            detect_series, detect_d_series, conc_series, states = Recog.detect_music(self, infer_series,
                    start, delta, duration, wav_offset, wav, sr,
                    ontology, interests, entire_abs_mean=entire_abs_mean, **states)
            calc_end = time.time()

            # Save cache
            infer_series_save = {k: v for k,v in infer_series.items() if start <= k[0] and k[0] <= start+clip_len}

            metadata["cache_list"].append({
                "start": float(start), "clip_len": clip_len, "abs_mean": float(entire_abs_mean), "calc_time": calc_end-calc_start,
                "wav_offset": float(wav_offset),
                "data": f"data{i}.pickle"})
            data = {"infer_series": infer_series_save,         "detect_series": detect_series,
                    "detect_series_denoised": detect_d_series, "state_series": conc_series,
                    "states": states}


            with open(save_dir / "metadata.yaml", 'w') as file:
                yaml.dump(metadata, file)

            with open(save_dir / metadata["cache_list"][-1]["data"], mode="wb") as f:
                pickle.dump(data, f)


            wav_offset = Recog.last_cur_time(states["prev_c_results"])
            start = states["cur_time"]

            i += 1


        return infer_series, detect_series, detect_d_series, conc_series


    @classmethod
    def load_cache(cls, save_dir, load_sr=100, load_mono=True, load_wav=True):
        save_dir = pathlib.Path(save_dir)

        with open(save_dir / "metadata.yaml", 'r') as file:
            metadata = yaml.safe_load(file)

        for i in range(len(metadata["cache_list"])):
            cache = metadata["cache_list"][i]

            with open(save_dir / cache["data"], 'rb') as file:
                cache["data"] = pickle.load(file)

            filename = metadata["filename"]

            if load_wav:
                wav, sr = librosa.load(filename, sr=int(load_sr), mono=show_mono, offset=cache["start"], duration=cache["clip_len"])
                cache["wav"] = wav
                cache["load_sr"] = sr

        return metadata

    @classmethod
    def merge_intervals(cls, metadata, big_thres=20, mini_thres=4, gap_thres=1.0):
        itvs = []
        cur_itv = None

        # raw detect series to (start,end) segments
        for cache in metadata["cache_list"]:
            d_series = cache["data"]["detect_series_denoised"]
            for prev_time, cur_time in utils.each_cons(sorted(d_series.keys()), 2):
                prev_label = d_series[prev_time]
                cur_label  = d_series[cur_time]
                # print(prev_time, prev_label, State.Music in prev_label)

                # MusicStart -> End or InPro
                if prev_label.value == (State.Music|State.Start).value and State.Music in cur_label:
                    cur_itv = [prev_time]

                # End
                if State.Music|State.End == prev_label:
                    if type(cur_itv) == list:
                        cur_itv.append(prev_time)
                        itvs.append(tuple(cur_itv))
                        cur_itv = None

        # [(indev of itvs, (itv)),...]
        big_itvs = filter(lambda i_itv: i_itv[1][1] - i_itv[1][0] >= big_thres, enumerate(itvs))
        #print([(v[0], utils.sec2time(v[1])) for v in  list(big_itvs)])

        result = {}
        for i, itv in big_itvs:
            result[i] = list(itv)
            pre_seq = reversed(range(i))
            sub_seq = range(i+1, len(itvs))

            for j in pre_seq:
                pre = itvs[j]
                if result[i][0] - pre[1] <= gap_thres and pre[1]-pre[0] >= mini_thres: # bit_itv start - pre end < gap_thres & pre >= mini_thres
                    result[i][0] = pre[0] # update start of itv
                else:
                    break

            for j in sub_seq:
                sub = itvs[j]
                if sub[0] - result[i][1] <= gap_thres and sub[1]-sub[0] >= mini_thres: # bit_itv start - sub end < gap_thres & sub >= mini_thres
                    result[i][1] = sub[1] # update end of itv
                else:
                    break

        #print([(i, utils.sec2time(itv)) for i, itv in  result.items()])

        return result, itvs



#M = State.Music
#T = State.Talking
#O = State.Other
#St = State.Start
#In = State.InProgress
#En = State.End
#Not = State.Not

def transition(prev_judge, cur_judge):
    OK = Label.OK
    BAD = Label.BAD

    if not State.Music in prev_judge and State.Music in cur_judge: # non Music -> Music
        if not State.End in cur_judge: # music start or InPro
            if State.Start in cur_judge:
                return [Label.Music_Start|OK, None]
            else:
                return [Label.Music_Already_Start|BAD, State.Music|State.Start]
        else: # next is End, without Starting
            return [Label.Music_End_withno_Start|BAD, State.Music|State.Start]


    elif State.Music in prev_judge and not State.Music in cur_judge: # Music -> non Music
        if not State.End in prev_judge: # music end not detected
            return [Label.Music_Already_End|BAD, State.Music|State.End]


    elif State.Music in prev_judge and State.Music in cur_judge: # Music -> Music
        if State.End in prev_judge and State.InProgress in cur_judge: # music not start but music (END->InPro)
            return [Label.Music_withno_Start|BAD, State.Music|State.Start]

        elif State.InProgress in prev_judge and State.InProgress in cur_judge: # InProgress -> InPro
            return [Label.Music_to_Music|OK, None]

        elif State.InProgress in prev_judge and State.Start in cur_judge: # Not End but Start (InPro -> Start)
            return [Label.Music_Start_withno_End|BAD, State.Music|State.End]

    return [OK, None]


class Label(Flag):
    # ! Music -> Music
    Music_Start = auto()
    Music_Already_Start = auto()
    Music_End_withno_Start = auto()

    # Music -> ! Music
    Music_Already_End = auto()

    # Music -> Music
    Music_withno_Start = auto()
    Music_to_Music = auto()
    Music_Start_withno_End = auto()

    # Type
    OK = auto()
    BAD = auto()



class State(Flag):
    Music = auto()
    Talking = auto()
    Other = auto()

    Start = auto()
    InProgress = auto()
    End = auto()
