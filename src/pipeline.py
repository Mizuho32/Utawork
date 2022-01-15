import concurrent.futures

class Pipeline:
    def __init__(self, recorder, buff_size, worker_size=2):
        self.recorder = recorder
        self.buff_size = buff_size

        self.buff_raw     = []
        self.buff_spectro = []
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=worker_size)


    def start(self, count, frames_per_record=1):
        while count > 0:
            self.recorder.record(frames_per_record)
            self.executor.submit(lambda : self.insert(self.recorder.frames))
            count-=1

    def insert(self, frames):
        for f in frames:
            self.buff_raw.append(f)

        for i in range(len(self.buff_raw)-self.buff_size):
            self.buff_raw.pop(0)
