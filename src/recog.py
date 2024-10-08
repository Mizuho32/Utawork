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
from matplotlib.axes import Axes


class Recog:
    logger = None


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
    def waveplot(cls, plt, librosa, y, sr, offset=0.0, max_sr=100, x_axis="time", ax=None, w=16, h=4):

        if offset >= 300: #FIXME: HELP ME
            x_axis = "s"

        if max_sr > 100:
            max_sr = 100

        if type(y) == torch.Tensor:
            y = y.to('cpu').detach().numpy().copy()

        if y.shape[0]==1: #mono
            y = y.reshape(y.shape[-1])

        if ax is None:
            plt.figure(figsize=(w, h))
            librosa.display.waveplot(y=y, sr=sr, offset=offset, max_sr=max_sr, x_axis=x_axis)
        else:
            librosa.display.waveplot(y=y, sr=sr, ax=ax, offset=offset, max_sr=max_sr, x_axis=x_axis)

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
    def classifyshow(cls, ontology: utils.Ontology, abst_scores_series, xstep=1, ax: Axes = None, title=""):
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
    def classify_show(cls, interests, audioset, ontology: utils.Ontology, result: torch.Tensor, xstep=1, ax: Axes = None, title=""):
        abst_concidx = ontology.absts_conc_indices(interests, audioset)

        # reduce by max
        abst_tensor = []
        for abst_id in sorted(abst_concidx.keys(), key=lambda i: ontology.to_name(i)):
            conc_idxs = abst_concidx[abst_id]
            abst_tensor.append(result[:, conc_idxs].max(dim=1).values)

        abst_tensor = torch.vstack(abst_tensor).transpose(1,0)

        ax.imshow(abst_tensor.transpose(0,1).cpu(), cmap='viridis', interpolation='nearest', aspect="auto")
        ax.set_title(title)

        #ax.set_xlabel('Time')
        #start, end = ax.get_xlim()
        #ax.xaxis.set_ticks(np.arange(start, end, xstep))

        labels = list(sorted(map(lambda i: ontology.to_name(i)[:7], abst_concidx.keys())))
        ax.set_yticks(np.arange(0, len(labels))+0.5*0)
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
            if torch.cuda.is_available():
                waveform = torch.from_numpy(y.astype(np.float32)).clone().cuda()
            else:
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

    # FIXME: wav should be instance variable, otherwise many times load happends
    def slice_wav(self, wav, sr, start, end):
        if wav is None:
            wav = self.wav #FIXME

        slice_start = int(sr*(start - self.wav_offset))
        slice_end   = int(sr*(end   - self.wav_offset))

        if slice_start < 0 or slice_end > wav.shape[-1]:
            Recog.logger.warn(f"Invalid slice {slice_start}:{slice_end} for {wav.shape} ({start}:{end} for {self.total_durat})")
            if slice_start < 0:
                old_wav_offset = self.wav_offset

                self.wav_offset = max(start  -1, 0)
                length = old_wav_offset - self.wav_offset

                Recog.logger.debug(f"-deltaload offset: {self.wav_offset}, duration:{length}")
                tmp_wav, _ = librosa.load(self.filename, sr=sr, mono=self.is_mono, offset=self.wav_offset, duration=length)

                wav = np.concatenate([tmp_wav, wav], axis=-1)

            if slice_end > wav.shape[-1]:
                end += 10 # FIXME: parametrize
                if end > self.total_durat:
                    end = self.total_durat

                tmp_wav_offset = self.wav_offset + wav.shape[-1]/sr
                length = end - tmp_wav_offset

                Recog.logger.debug(f"+deltaload offset: {tmp_wav_offset}, duration:{length}")
                tmp_wav, _ = librosa.load(self.filename, sr=sr, mono=self.is_mono, offset=tmp_wav_offset, duration=length)
                Recog.logger.debug(f"delta: {tmp_wav.shape}, wav: {wav.shape}")
                wav = np.concatenate([wav, tmp_wav], axis=-1)

            self.wav = wav

            return Recog.slice_wav(self, self.wav, sr, start, end)



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
                if State.End   in prev_state and State.Start in cur_state or \
                   State.Start in prev_state and State.End   in cur_state:
                    try:
                        #print(f"pop {prev_event_time}, {cur_event_time}")
                        denoised.pop(prev_event_time)
                        denoised.pop(cur_event_time)
                        if State.End in prev_state and State.Start in cur_state:
                            # FIXME: cases not only for music
                            denoised[prev_event_time] = State.Music|State.InProgress
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
    def last_cur_time(cls, prev_c_results, nth_latest=1): # FIXME: LINQ
        min_times = list(sorted(map(lambda cr: min(map(lambda itv:itv[0], cr.keys())), prev_c_results)))
        return min_times[-nth_latest]


    def detect_music(self, series, start, delta, duration, wav_offset, wav, sr, ontology, interests,
            music_length=4*60, music_check_len=20, thres=1.0,
            min_interval=5, big_interval=15, stop=np.infty,

            cur_time = None,
            prev_judge = None, prev_c_results= None, prev_judges_d = None,
            prev_abs_mean = 0,
            interval_plan = [],
            detect_back_target = None, entire_abs_mean = 0 ):

        self.wav_offset = wav_offset
        self.wav = wav
        entire_abs_mean = entire_abs_mean or np.abs(self.wav).mean()

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

        wav_len = self.wav.shape[-1]
        self_wav = None # FIXME

        while cur_time < stop and sr*(cur_time+duration - wav_offset) < wav_len:

            # do inference
            try:
                judges, c_result = Recog.judge_segment(self, ontology, series, cur_time, delta, duration, self_wav, sr, ontology, interests)
            except IndexError as ex:
                print(ex)
                raise ex
                break

            cur_abs_mean = np.abs(Recog.slice_wav(self, self_wav, sr, cur_time, cur_time+duration)).mean()

            Recog.logger.debug(utils.judges2str(judges))

            # denoise inference
            judges_d = Recog.judges_denoised(judges, c_result, thres)

            if not judges_d.keys():
                if interval_plan:
                    cur_time += interval_plan.pop()
                else:
                    cur_time += min_interval
                continue

            cur_judge = judges_d[max(judges_d.keys())] # get most recent State

            judgess, c_results, judgess_d = [judges], [c_result], [judges_d]

            # detect chagnes
            if prev_judge != None:
                label, detect_back_target = transition(prev_judge, cur_judge)

                # ! Music -> Music
                if Label.Music_Start in label or Label.Music_Already_Start in label: # music start or InPro
                    is_starting, next_cur_time, judgess, c_results = \
                        Recog.is_music_starting(self, series, cur_time, delta, duration, music_check_len, min_interval, self_wav, sr, ontology, interests, thres=thres)
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
                    Recog.logger.debug(f"detect_back {detect_back_target}")
                    trial = 1
                    back_start = cur_time
                    back_prev_js_d = prev_judges_d

                    #FIXME: use time ordered dict
                    result_d_keys = list(sorted(result_d.keys()))

                    while True:
                        #back_end = Recog.last_cur_time(prev_c_results, nth_latest=trial)
                        back_end = max(back_prev_js_d.keys())
                        back_prev_judge = back_prev_js_d[back_end]
                        Recog.logger.debug(f" {trial}th trial {utils.sec2time(back_start)} {cur_judge}->{utils.sec2time(back_end)} {back_prev_js_d}")

                        detected_judge, d_js, tmp_j, tmp_c = Recog.back_to_change(self, back_prev_js_d, detect_back_target, series, back_start, delta, duration, back_end, self_wav, sr, ontology, interests, thres = thres)

                        try:
                            if d_js and d_js[-1][back_start] != cur_judge: # back_start nearest one has back_start time event
                                d_js[-1].pop(back_start) # cur_judge is more reliable
                        except (IndexError, KeyError) as e:
                            pass

                        # FIXME?: should expire old judges?
                        judgess, c_results, judgess_d = [*tmp_j, *judgess], [*tmp_c, *c_results], [*d_js, *judgess_d]

                        # found the target or
                        # not found but prev judge is not the same as current (so there should exist the target btw them but not found, terminate unfortunately)
                        if not detected_judge == None or \
                                detected_judge == None and back_prev_judge != cur_judge:
                            break

                        trial += 1
                        back_start = back_end
                        try:
                            k = result_d_keys[-trial]
                            back_prev_js_d = {k: result_d[k]}
                        except IndexError: # no more item
                            break

                    #for tmp in judgess_d:
                    #    print(utils.js2s(tmp, "->", split=", "))

                    if detected_judge == None:
                        Recog.logger.debug(f"Failed to find {detect_back_target} (at {cur_time})")

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
        hypothesis = []
        #print("prev: ", prev_judges_d)

        def cr_min(cr): # FIXME: make specialized class
            return min(map(lambda itv: itv[0], cr.keys()))

        def inserts(i, c_result, judges, judges_d):
            c_results.insert(i, c_result)
            judgess  .insert(i, judges)
            judgess_d.insert(i, judges_d )

        def find_index():
            cur = cr_min(c_result)
            for i, cr in enumerate(c_results):
                if cur < cr_min(cr):
                    return i
            return len(c_results) # append

        def no_contradict_add(c_result, judges, judges_d): #FIXME: make specialized class
            idx = find_index()

            # no contradict insert
            if idx != 0:
                prev_js = judgess_d[idx-1]
                for t in prev_js.keys(): # shift judges who has the same value
                    try:
                        j = judges_d.pop(t)
                        judges_d[utils.round(t+delta, 1)] = j
                    except KeyError:
                        pass
            inserts(idx, c_result, judges, judges_d)


        # search even -> odd, 1delta overwrap
        for j in range(2):
            for i in map(lambda i: i*2, range(int(len(itvs)/2+1))):
                try:
                    time, duration = itvs[j+i]
                except IndexError:
                    break
                judges, c_result = Recog.judge_segment(self, ontology, series, time, delta, duration, wav, sr, ontology, interests)
                js_d = Recog.judges_denoised(judges, c_result, thres)
                no_contradict_add(c_result, judges, js_d)

                # includes target for latest added judges_d? and consistent?
                found_target = any(map(lambda etime_st: target == etime_st[1], js_d.items()))
                is_consistent = Recog.consistent_judge_series([*judgess_d, prev_judges_d]) # FIXME: incremental consistency check

                #print(f"{utils.sec2time(time)}", judges, js_d, found_target, is_consistent)

                if found_target and is_consistent:
                    return js_d, judgess_d, judgess, c_results
                elif found_target:
                    hypothesis.append(judgess_d)
                elif hypothesis and is_consistent:
                    # return first found hyp. FIXME? to return latest one?
                    return hypothesis[0], judgess_d, judgess, c_results
                    #print(sorted([*judgess_d, prev_judges_d], key=lambda d: min(d.keys())))
                    #print(sorted([*judgess  , prev_judges_d], key=lambda d: min(d.keys())))
                    #print(sorted(c_results, key=lambda d: min(map(lambda itv: itv[0], d.keys()))))

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


    def detect_music_main(self, filename, save_dir, start, clip_len, delta, duration, ontology, interests, sr, is_mono=False, infer_series = {}, stop_time=np.infty, ignore_steps=[], cache_overwrite=False, console_print=True, cache_offset=-1):

        self.is_mono = is_mono
        self.filename = filename

        save_dir = pathlib.Path(save_dir)
        if not save_dir.exists():
            raise FileNotFoundError(f"No such a directory {save_dir}")

        utils.killLogger(Recog.logger)
        Recog.logger  = utils.get_module_logger("detect", save_dir, console_print=console_print)
        Recog.logger.info(f"\n  Start {datetime.datetime.now()}")

        # Load cache
        metad_exist = (save_dir / "metadata.yaml").exists()
        if not cache_overwrite and metad_exist:

            with open(save_dir / "metadata.yaml", 'r') as file:
                metadata = yaml.safe_load(file)

            idx = len(metadata["cache_list"]) + cache_offset # last data index
            means = list(map(lambda c: c["abs_mean"], metadata["cache_list"]))

            with open(save_dir / metadata["cache_list"][idx]["data"], 'rb') as file:
                states = pickle.load(file)["states"]

            start = states["cur_time"]

            if idx > 0:
                wav_offset = Recog.last_cur_time(states["prev_c_results"])
                if wav_offset > start: # FIXME: when detect_start happened at previous detection?
                    wav_offset = start

            else:
                wav_offset = start

            idx += 1

        else:
            wav_offset = start
            means = []
            states = {}

            if metad_exist:
                with open(save_dir / "metadata.yaml", 'r') as file:
                    metadata = yaml.safe_load(file)
            else:
                metadata = {"filename": filename, "delta": delta, "duration": duration, "mono": is_mono,
                            "sr": sr, "cache_list": []}
            idx = 0


        self.total_durat = librosa.get_duration(filename=filename)
        total_count_upper = int(np.ceil(self.total_durat/clip_len))

        detect_series, detect_d_series, conc_series = {}, {}, {} # FIXME, just for init

        for i in range(idx, total_count_upper+1):
            if not start+clip_len <= stop_time:
                break

            Recog.logger.debug(f"{i} Start:{start}, offset:{wav_offset}, len:{clip_len}")
            wav, sr = librosa.load(filename, sr=sr, mono=is_mono, offset=wav_offset, duration=clip_len)

            #print(f"{sr*(start-wav_offset)} < {wav.shape[-1]}")
            if not sr*(start-wav_offset) < wav.shape[-1]: # empty
                break

            # load infer_series cache if exists
            if i < len(metadata["cache_list"]):
                pkl_file =  save_dir / metadata["cache_list"][i]["data"]
                if pkl_file.exists():
                    with open(pkl_file, 'rb') as file:
                        for k, v in pickle.load(file)["infer_series"].items():
                            infer_series[k] = v


            # calc abs mean
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

            utils.append_or_overwrite(metadata["cache_list"], i, {
                "start": float(start), "clip_len": clip_len, "abs_mean": float(entire_abs_mean), "calc_time": calc_end-calc_start,
                "wav_offset": float(wav_offset),
                "data": f"data{i}.pickle"})
            data = {"infer_series": infer_series_save,         "detect_series": detect_series,
                    "detect_series_denoised": detect_d_series, "state_series": conc_series,
                    "states": states}


            with open(save_dir / "metadata.yaml", 'w') as file:
                yaml.dump(metadata, file)

            with open(save_dir / metadata["cache_list"][i]["data"], mode="wb") as f:
                pickle.dump(data, f)


            wav_offset = Recog.last_cur_time(states["prev_c_results"])
            start = states["cur_time"]

            i += 1


        return infer_series, detect_series, detect_d_series, conc_series


    @classmethod
    def load_cache(cls, save_dir, load_sr=100, show_mono=True, load_wav=True, old_metadata=None):

        if type(load_wav) is list:
            load_wav = list(map(lambda time: utils.time2sec(time), load_wav))

        save_dir = pathlib.Path(save_dir)

        with open(save_dir / "metadata.yaml", 'r') as file:
            metadata = yaml.safe_load(file)

        for i in range(len(metadata["cache_list"])):
            cache = metadata["cache_list"][i]

            if old_metadata:
                cache["data"] = old_metadata["cache_list"][i]["data"]
            else:
                with open(save_dir / cache["data"], 'rb') as file:
                    cache["data"] = pickle.load(file)

            filename = metadata["filename"]


            if old_metadata and "wav" in old_metadata["cache_list"][i] \
                    and type(old_metadata["cache_list"][i]["wav"]) == np.ndarray:
                c = old_metadata["cache_list"][i]
                wav, sr = c["wav"], c["load_sr"]
            else:
                if load_wav == True:
                    wav, sr = librosa.load(filename, sr=int(load_sr), mono=show_mono, offset=cache["start"], duration=cache["clip_len"])
                elif type(load_wav) == list and \
                    any(map(lambda time: cache["start"] <= time and time <= cache["start"]+cache["clip_len"], load_wav)):
                    print(f'Load {i}-th, {utils.sec2time(cache["start"])} to {utils.sec2time(cache["start"]+cache["clip_len"])}')
                    wav, sr = librosa.load(filename, sr=int(load_sr), mono=show_mono, offset=cache["start"], duration=cache["clip_len"])
                else:
                    wav, sr = None, None

            if type(wav) == np.ndarray and sr != None:
                cache["wav"] = wav
                cache["load_sr"] = sr

        for i in range(len(metadata["cache_list"])):
            cache = metadata["cache_list"][i]
            if "wav" in cache and type(cache["wav"]) == np.ndarray:
                print(f'Loaded {i}-th, {utils.sec2time(cache["start"])} to {utils.sec2time(cache["start"]+cache["clip_len"])}')

        return metadata

    @classmethod
    def merge_intervals(cls, metadata, big_thres=20, mini_thres=4, gap_thres=1.0, allow_ill=False):
        itvs = []
        cur_itv = None

        # raw detect series to (start,end) segments
        non_empty_cache_list = list(filter(lambda cache: cache["data"]["detect_series_denoised"].keys(),
                metadata["cache_list"]))

        for i, cache in enumerate(non_empty_cache_list):
            d_series = cache["data"]["detect_series_denoised"]
            sorted_times = sorted(d_series.keys())

            if not sorted_times:
                continue

            # for terminal caches, Start and End label
            if i==0: #first
                sorted_times.insert(0, sorted_times[0]-1)

            if i == len(non_empty_cache_list)-1 : # last
                sorted_times.append(sorted_times[-1]+1)

            for prev_time, cur_time in utils.each_cons(sorted_times, 2):
                try:
                    prev_label = d_series[prev_time]
                except KeyError:
                    prev_time = sorted_times[1] # original time 0
                    prev_label = State.Start

                try:
                    cur_label  = d_series[cur_time]
                except KeyError:
                    cur_label  = State.End

                #print(prev_time, prev_label, State.Music in prev_label)

                if State.InProgress in prev_label and State.InProgress in cur_label:
                    continue

                # non Music -> Music
                # FIXME: condition should be MusicStart -> End or InPro
                if prev_label == State.Music|State.Start and State.Music in cur_label or \
                    (not State.InProgress in prev_label and State.InProgress in cur_label and allow_ill):

                    #if not State.InProgress in prev_label and State.InProgress in cur_label:
                    #    print(f"Ill interval start at {utils.sec2time(prev_time)} ({prev_time})")
                    cur_itv = [prev_time]
                    continue


                # End
                #if State.Music|State.End == prev_label:
                if State.Music|State.End == prev_label or \
                    (State.InProgress in prev_label and not State.InProgress in cur_label and allow_ill):
                    if type(cur_itv) == list:
                        cur_itv.append(prev_time)
                        itvs.append(tuple(cur_itv))
                        cur_itv = None

        # Filter big intervals
        # [(indev of itvs, (itv)),...]
        big_itvs = list( filter(lambda i_itv: i_itv[1][1] - i_itv[1][0] >= big_thres, enumerate(itvs)) )
        #print("bigs:\n", [(v[0], utils.sec2time(v[1])) for v in  list(big_itvs)])

        # Merge intervals to big itvs where intervals are bigger than mini_thres and gap btw them is less then gap_thres
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

    @classmethod
    def to_audtxt(cls, itv_ar):
        return "\n".join(map(lambda itv: "\t".join(map(lambda sec: str(sec), itv)), itv_ar))


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
