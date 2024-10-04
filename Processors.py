from multiprocessing import Event, Process
from queue import Empty

from PIL import Image, ImageOps

default_image = Image.new("RGB", (480, 360))


class ScaleFilter:
    def __init__(self, outputs, manager):
        self.outputs = outputs
        self.image = default_image
        self.input = manager.Queue()

        self.stopped = Event()
        self.proc = Process(target=self.run, daemon=True)
        self.proc.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                item = self.input.get(timeout=0.2)
                conv = ImageOps.scale(item, 0.8)
                for i in self.outputs:
                    i.put(conv)
            except Empty:
                continue

    def graceful_exit(self):
        self.stopped.set()
        self.proc.join()


class InvertFilter:
    def __init__(self, outputs, manager):
        self.outputs = outputs
        self.image = default_image
        self.input = manager.Queue()

        self.stopped = Event()
        self.proc = Process(target=self.run, daemon=True)
        self.proc.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                item = self.input.get(timeout=0.2)
                conv = ImageOps.invert(item)
                for i in self.outputs:
                    i.put(conv)
            except Empty:
                continue

    def graceful_exit(self):
        self.stopped.set()
        self.proc.join()


class MirrorFilter:
    def __init__(self, outputs, manager):
        self.outputs = outputs
        self.image = default_image
        self.input = manager.Queue()

        self.stopped = Event()
        self.proc = Process(target=self.run, daemon=True)
        self.proc.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                item = self.input.get(timeout=0.2)
                conv = ImageOps.mirror(item)
                for i in self.outputs:
                    i.put(conv)
            except Empty:
                continue

    def graceful_exit(self):
        self.stopped.set()
        self.proc.join()


class GrayscaleFilter:
    def __init__(self, outputs, manager):
        self.outputs = outputs
        self.image = default_image
        self.input = manager.Queue()

        self.stopped = Event()
        self.proc = Process(target=self.run, daemon=True)
        self.proc.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                item = self.input.get(timeout=0.2)
                conv = ImageOps.grayscale(item)
                for i in self.outputs:
                    i.put(conv)
            except Empty:
                continue

    def graceful_exit(self):
        self.stopped.set()
        self.proc.join()
