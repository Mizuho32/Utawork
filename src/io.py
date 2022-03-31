import pyaudio
import numpy as np
import torch
import torchaudio
import scipy.signal as sps

class Record:

    def __init__(self, device_info, sample_rate, chunk_size_split=2, channels=2, torch_mode=True):
        self.device_info = device_info
        self.sample_rate = sample_rate # sr of model
        self.device_sample_rate = int(device_info["defaultSampleRate"])   # wave sr
        self.chunk_size = int(self.device_sample_rate / chunk_size_split)
        self.channels = channels
        self.torch_mode = torch_mode

        self.p = None
        self.stream = None

        if torch_mode:
            torch.concatenate = torch.cat
            self.nt = torch
            self.transform = torchaudio.transforms.Resample(self.device_sample_rate, self.sample_rate)
        else:
            self.nt = np

        print("Inst")

    def __del__(self):
        print("Deconst")
        if self.stream is not None:
            self.disconnect()

    def sec2frame(self, second):
        frames = int(self.device_sample_rate / self.chunk_size * second)
        actual_range = (self.chunk_size / self.device_sample_rate)*frames # in sec
        return frames, actual_range

    def connect(self):
        if self.p is None:
            self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
                format=pyaudio.paInt16, channels=self.channels, rate=self.device_sample_rate, input=True,
                frames_per_buffer=self.chunk_size, input_device_index=self.device_info["index"])

    def disconnect(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

        self.stream = None
        self.p = None

    def reconnect(self):
        self.disconnect()
        self.connect()

    def record(self, frame_num):
        if self.stream is None:
            self.connect()

        self.frames = []
        for i in range(0, frame_num):
            data = self.stream.read(self.chunk_size)
            if self.torch_mode:
                data = bytearray(data)
            # https://www.kaggle.com/general/213391
            #rawdata = (self.nt.frombuffer(data, dtype=self.nt.int16)/(4*2**15)).reshape(-1, self.channels).transpose(1, 0)
            rawdata = (self.nt.frombuffer(data, dtype=self.nt.int16)/(1*2**15)).reshape(-1, self.channels).transpose(1, 0)
            #print(self.nt, type(rawdata), type(frame))
            self.frames.append(self.sr_conv(rawdata))

        return self.frames

    def concat(self):
        return self.nt.concatenate(self.frames, axis=1)

    def sr_conv(self, raw_frame):
        if self.device_sample_rate == self.sample_rate:
            return raw_frame

        if self.torch_mode:
            return self.transform(raw_frame)
        else:
            # https://stackoverflow.com/questions/30619740/downsampling-wav-audio-file
            number_of_samples = round(raw_frame.shape[1] * float(self.sample_rate) / self.device_sample_rate)
            return sps.resample(raw_frame, number_of_samples, axis=1)
