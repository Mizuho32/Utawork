import pathlib, glob
import pickle
from typing import List, Dict, Tuple
from enum import Flag, auto

import librosa
import torch
import numpy as np
from py_linq import Enumerable as E

import whisper
from . import utils, audioset
from .infer_cache import InferCache
from .detector import Config

#from matplotlib.axes import Axes

class Transcription:
    # [start ,end], text
    def __init__(self, segment: np.ndarray, text: str, lang: str):
        self.segment = segment
        self.text = text
        self.lang = lang

        self.title = ""
        self.artist = ""

        self.search_word: str = ""
        self.search_result: List[str] = []
        self.llm_result: str = ""

    @classmethod
    def Renew(cls, transcription):
        new = cls(np.empty(()), "", "")

        for attr, value in transcription.__dict__.items():
            setattr(new, attr, value)

        return new

class Transcriber:

    def __init__(self, model: whisper.Whisper, config: Config, model_sr=16000):
        self.model = model
        self.model_sr = model_sr
        self.config = config

        self.transcribe_dir = self.config.transcript_cache_dir / config.input_path.stem
        self.prepare()

    def prepare(self,):
        if not self.transcribe_dir.exists():
            self.transcribe_dir.mkdir(parents=True)

    def do_cache(self, transcribes: List[Transcription]):
        with open(self.transcribe_dir / f"{self.config.input_path.stem}.pkl", "wb") as h:
            pickle.dump(transcribes, h)

    # interval: min
    def progress(self, idx: int):
        config = self.config
        interval_idx = int(config.print_interval * 60 / config.cut_duration)

        if idx % interval_idx == 0:
            print(f"At {utils.sec2time(idx*config.cut_duration)}")

    def main(self) -> List[Transcription]:

        config = self.config
        music_intervals: np.ndarray = np.vstack([
            np.empty((0, 2)),
            np.loadtxt(config.input_path.parent / f"{config.input_path.stem}.txt", dtype=float, delimiter="\t")])
        transcriptions: List[Transcription] = []

        try:
            for segment in music_intervals:
                if segment[1] - segment[0] < config.thres_set.transc_long_thres:
                    print("whisper skip", segment)
                    continue

                print("whisper", segment)
                transcriptions.append(self.infer_segment(segment))
        except Exception as ex:
            self.do_cache(transcriptions)
            raise ex

        self.do_cache(transcriptions)

        return transcriptions

    def infer_segment(self, segment: np.ndarray) -> Transcription:
        start, end = segment
        duration = end - start

        num_split = int(duration//30)
        steps = np.hstack([np.array(range(num_split + 1)) * 30 + start, end])

        text = ""
        lang = ""
        for idx, (start, end) in enumerate(utils.each_cons(steps, 2)):

            try:
                audio, _ = librosa.load(self.config.input_path, sr=self.model_sr, offset = start, duration=end-start)
            except ValueError as ex:
                print("librosa.load:", ex)
                continue

            audio = whisper.pad_or_trim(audio)

            # make log-Mel spectrogram and move to the same device as the model
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)

            if idx == 0:
                # detect the spoken language
                _, probs = self.model.detect_language(mel)
                lang: str = max(probs, key=probs.get) # type: ignore
                print(f"Detected language: {lang}")

            # decode the audio
            options = whisper.DecodingOptions()
            result = whisper.decode(self.model, mel, options)

            text += result.text # type: ignore

        return Transcription(segment, text, lang)

    def get_cache(self) -> List[Transcription]:
        return utils.load_pickle(self.transcribe_dir / f"{self.config.input_path.stem}.pkl")