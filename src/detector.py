import pathlib, glob
import pickle
from typing import List, Dict, Tuple
from enum import Flag, auto

import librosa
import torch
import numpy as np
from py_linq import Enumerable as E

from .audioclassifier import AudioClassifier
from . import utils, audioset
from .infer_cache import InferCache

#from matplotlib.axes import Axes

class Label(Flag):
    Music = auto()
    Talking = auto()
    Other = auto()

    Start = auto()
    InProgress = auto()
    End = auto()

class Chunk:
    def __init__(self, intervals: Dict[Label, np.ndarray]):
        self.intervals = intervals

class Threshold:
    def __init__(self, thres: float, human_thres: float, music_joint_thres: float, human_joint_thres: float, adj_thres: float, long_thres: float, hs_rate_thres: float):
        self.thres = thres
        self.human_thres = human_thres
        self.music_joint_thres = music_joint_thres
        self.human_joint_thres = human_joint_thres

        self.adj_thres = adj_thres
        self.long_thres = long_thres
        self.hs_rate_thres = hs_rate_thres
        

class Config:
    def __init__(self, input_path: pathlib.Path,  cut_duration: float, thres_set: Threshold, interests: List[dict], cache_interval: int, model_sr:int =32000):
        self.input_path = input_path
        self.cache_dir = input_path.parent / "infer_cache"
        self.cache_interval = cache_interval

        self.interests = interests
        self.cut_duration = cut_duration
        self.thres_set = thres_set

        self.model_sr = model_sr

class Detector:
    logger = None


    def __init__(self, classifier: AudioClassifier, ontology: utils.Ontology, audioset: audioset.AudioSet, config: Config):
        self.classifier = classifier
        self.ontology = ontology
        self.audioset = audioset

        self.config = config

    def prepare(self,):
        self.cache_dir = self.config.cache_dir

        if not self.cache_dir.exists():
            self.cache_dir.mkdir()

    def do_cache(self, index, offset, duration, abst_tensor, music_intervals):
        cache = InferCache(index, offset, duration, abst_tensor, music_intervals)

        with open(self.cache_dir / f"{index}.pkl", "wb") as h:
            pickle.dump(cache, h)

    def main(self, start_offset: float) -> np.ndarray:
        self.prepare()

        config = self.config
        offset = start_offset
        idx = 0
        music_intervals: List[np.ndarray] = [np.empty((0,2))]
        num_abst_cls = len(self.classifier.abst_concidx.keys())

        while True:
            cache_offset = offset
            cache_idx = idx
            cache_duration = 0

            cache_abst_tensors: List[torch.Tensor] = [torch.empty((0, num_abst_cls))]
            cache_music_intervals: List[np.ndarray] = [np.empty((0,2))]

            for local_idx in range(config.cache_interval):
                try:
                    waveform, sr = librosa.load(config.input_path, sr=config.model_sr, offset=offset, duration=config.cut_duration)
                except ValueError:
                    print(f"End {config.input_path}")
                    waveform = None
                    break

                output_dict = self.classifier.infer(waveform)
                abst_tensor = self.classifier.abst_tensor(output_dict["framewise_output"].cpu()[0], config.interests, self.ontology, self.audioset)
                cache_abst_tensors.append(abst_tensor)

                tmp = AudioClassifier.music_intervals(abst_tensor, offset, config.cut_duration, config.thres_set.thres)
                if len(tmp):
                    cache_music_intervals.append(tmp)

                idx += 1
                offset += config.cut_duration

                cache_duration += len(waveform)/sr

            if type(waveform) is type(None):
                break

            #print([itvs.shape for itvs in cache_music_intervals])
            #print([itvs.shape for itvs in cache_abst_tensors])
            tmp = np.vstack(cache_music_intervals)
            music_intervals.append(tmp)
            self.do_cache(cache_idx, cache_offset, cache_duration, torch.vstack(cache_abst_tensors), tmp)


        return np.vstack(music_intervals)
    
    def get_cache(self, time: float, duration: float, config: Config) -> Tuple[float, float, torch.Tensor, np.ndarray]: # time fixed, duration fixed, abst tensor, intervals
        cache_dir = config.cache_dir

        start_idx = time // config.cut_duration
        n = (time+duration) // config.cut_duration - start_idx

        # 9 = (11//3)*3
        indices = list(set([ (idx//config.cache_interval)*config.cache_interval for idx in range(start_idx, start_idx+n+1)]))
        #print(indices, list(range(start_idx, start_idx+n+1)), n)
        caches: List[InferCache] = [utils.load_pickle(cache_dir / f"{idx}.pkl") for idx in indices]


        def get_time_in_cache(time: float, cache: InferCache, increment=0):
            abst_resolution, abst_num_cls = cache.abst_tensor.shape
            delta_step = min(int( (time - cache.offset) / cache.duration * abst_resolution ) + increment, abst_resolution)
            delta = cache.duration * delta_step / abst_resolution

            return delta + cache.offset, delta_step

        num_abst_cls = len(self.classifier.abst_concidx.keys())
        abst_tensors: List[torch.Tensor] = [torch.empty((0, num_abst_cls))]
        intervals: List[np.ndarray] = [np.empty((0,2))]

        end_step = 0

        for idx, cache in enumerate(caches):
            if idx == 0:
                start_cache = cache
                start_time, start_delta_step = get_time_in_cache(time, start_cache)

            if idx == len(caches)-1:
                end_cache = cache
                end_time, end_delta_step = get_time_in_cache(time+duration, end_cache)
                end_step += end_delta_step
            else:
                abst_resolution, _ = cache.abst_tensor.shape
                end_step += abst_resolution
        
            abst_tensors.append(cache.abst_tensor)
            intervals.append(cache.music_intervals)
        
        abst_tensor = torch.vstack(abst_tensors)
        mi = np.vstack(intervals)
        

        return start_time, end_time-start_time, abst_tensor[start_delta_step:(end_step+1), :], mi[ (mi[:, 0] >= start_time) & (mi[:, 0] <= end_time)]
    
    def concat_cached_abst(self) -> Tuple[torch.Tensor, float, float]:
        cache_paths: List[pathlib.Path] = sorted(E(glob.glob(f"{self.config.cache_dir}/*.pkl")).select(lambda path: pathlib.Path(path)), key=lambda path: int(path.stem))
        num_abst_cls = len(self.classifier.abst_concidx.keys())
        all_abst_tensors: List[torch.Tensor] = [torch.empty((0, num_abst_cls))]
        duration = 0

        for path in cache_paths:
            cache: InferCache = utils.load_pickle(path)
            all_abst_tensors.append(cache.abst_tensor)
            duration += cache.duration

        return torch.vstack(all_abst_tensors), 0, duration

    def abst_tensor2intervals(self, abst_tensor, start_time, duration):
        config = self.config
        thres_set = config.thres_set
        filter = lambda t: wise_filter(t, thres_set.thres, (thres_set.music_joint_thres, thres_set.human_joint_thres))

        music_intervals = AudioClassifier.music_intervals(abst_tensor, start_time, duration, None, predicate=filter)
        human_speech_intervals = AudioClassifier.music_intervals(abst_tensor, start_time, duration, thres_set.thres, target_index=2)

        return precise_music_intervals(music_intervals, human_speech_intervals, thres_set.adj_thres, thres_set.long_thres, thres_set.hs_rate_thres)
        
    
# adj_thres: inc sec
def precise_music_intervals(music_intervals: np.ndarray, human_speech_intervals: np.ndarray, adj_thres: float, long_thres: float, hs_rate_thres: float) -> np.ndarray:

    final_music_intervals: List[np.ndarray] = [np.empty((0,2))]
    music_intervals2 = np.vstack([music_intervals, np.array([-1, -1])])

    hs_idx = 0

    if len(music_intervals):

        start_time, end_time = music_intervals[0]
        for idx in range(music_intervals.shape[0]):
            pre, nxt = music_intervals2[idx], music_intervals2[idx+1]
            end = (nxt < 0).all()

            if nxt[0] - pre[1] <= adj_thres and not end:
                continue

            #  pre << nxt enough
            end_time = pre[1]

            try:
                hs_durat = 0

                while True:
                    start_hs, end_hs = human_speech_intervals[hs_idx]

                    if end_hs < start_time:
                        hs_idx += 1
                    elif start_time <= start_hs <= end_time or start_time <= end_hs <= end_time:
                        start_hs = max(start_hs, start_time)
                        end_hs = min(end_time, end_hs)
                        hs_durat += end_hs - start_hs
                    
                        hs_idx += 1
                    else:
                        hs_idx -= 1
                        break

            except IndexError:
                pass
            
            if end_time - start_time >= long_thres and hs_durat / (end_time - start_time) <= hs_rate_thres:
                final_music_intervals.append([start_time, end_time])

            start_time, end_time = nxt

    return np.vstack(final_music_intervals)


def to_audacity(itvs):
    return str.join("\n", [str.join("\t", map(lambda elm: "%.3f" % elm, row)) for row in itvs])

# joint_thres: [music thres, human speech thres], abst_tensor > music and abst_tensor < human
def wise_filter(abst_tensor: torch.Tensor, music_only_thres: float, joint_thres: Tuple[float, float]):
    music_joint_thres, human_joint_thres = joint_thres
    return (abst_tensor[:, 3] > music_only_thres) | ((abst_tensor[:, 2] < human_joint_thres) & (abst_tensor[:, 3] > music_joint_thres))