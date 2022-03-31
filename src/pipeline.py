import concurrent.futures

from . recog import Recog

class Pipeline:
    def __init__(self, recorder, buff_size, worker_size=2):
        self.recorder = recorder
        self.buff_size = buff_size

        self.buff_raw     = []
        self.buff_spectro = []
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=worker_size)

        self.inserted = False
        self.end = False


    def start(self, count, fire_aftrinsert, frames_per_record=1):
        while count > 0:
            frames = self.recorder.record(frames_per_record)
            self.executor.submit(lambda : self.insert(frames, fire_aftrinsert))
            count-=1

        self.end = True

    def insert(self, frames, fire_aftrinsert):
        for f in frames:
            self.buff_raw.append(f)
            self.buff_spectro.append(Recog.fbank(f.cuda(), self.recorder.sample_rate, 0))

        for i in range(len(self.buff_raw)-self.buff_size):
            self.buff_raw.pop(0)
            self.buff_spectro.pop(0)

        if fire_aftrinsert is not None:
            fire_aftrinsert(frames, self.buff_raw)

        self.inserted = True

    def lock(self):
        while not self.inserted and not self.end:
            None
        self.inserted = False
