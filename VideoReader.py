from threading import Thread
from multiprocessing import Event, Process

from time import sleep
from queue import Empty

from PIL import Image
import cv2
from cv2_enumerate_cameras import enumerate_cameras


default_image = Image.new("RGB", (480, 360))


class Camera:
    def __init__(self):
        self.choices = {}
        self.active = ""
        self.cam = None
        self.enabled = True

        self.update_cam_list()

    def update_cam_list(self):
        self.choices = {}
        for cam in enumerate_cameras():
            self.choices[cam.name] = cam.index

        if self.active not in self.choices:
            self.active = self.get_cam_list()[0]
            self.force_reload(self.active)

    def get_cam_list(self):
        return list(self.choices.keys())

    def force_reload(self, new_camera: str):
        if self.cam is not None:
            self.cam.release()

        if new_camera is not None:
            self.active = new_camera
        self.cam = cv2.VideoCapture(self.choices[self.active])

    def lazy_reload(self, new_camera: str):
        if self.active == new_camera:
            return

        self.force_reload(new_camera)

    def take_screenshot(self):
        if not self.enabled:
            return default_image

        _, img = self.cam.read()
        if img is None:
            return default_image

        width = self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)

        if height == 0:
            return default_image

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(
            img, (int(360 * width // height), 360), interpolation=cv2.INTER_LINEAR
        )
        return Image.fromarray(img)

    def release(self):
        if self.cam is not None:
            self.cam.release()

    def disable(self):
        self.enabled = False
        self.release()

    def enable(self):
        self.enabled = True
        self.force_reload(self.active)


class FileVideoStream:
    def __init__(self, video_filename: str):
        self.video = cv2.VideoCapture(video_filename)
        self.spf = 1 / self.video.get(cv2.CAP_PROP_FPS)
        self.cur_image = None

        self.unpaused = Event()
        self.unpaused.set()

        self.finished = Event()
        self.thr = Thread(target=self.stream_video_forever, daemon=True)
        self.thr.start()

    def stream_video_forever(self):
        while not self.finished.is_set():
            self.unpaused.wait()
            s, self.cur_image = self.video.read()
            if not s:
                self.finished.set()
                break

            sleep(self.spf)

    def pause(self):
        self.unpaused.clear()

    def unpause(self):
        self.unpaused.set()

    def take_screenshot(self):
        img = self.cur_image
        if img is None:
            return default_image

        width = self.video.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.video.get(cv2.CAP_PROP_FRAME_HEIGHT)

        if height == 0:
            return default_image

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(
            img, (int(360 * width // height), 360), interpolation=cv2.INTER_LINEAR
        )
        return Image.fromarray(img)

    def graceful_exit(self):
        self.unpaused.set()
        self.finished.set()
        self.thr.join()


class VideoSource:
    def __init__(self, command_q, outputs):
        self.camera = None
        self.outputs = outputs
        self.commands = command_q

        self.file_video = False
        self.file = ""
        self.video_player = None

        self.stopped = Event()
        self.proc = Process(target=self.run, daemon=True)
        self.proc.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                while True:
                    comm = self.commands.get(timeout=0.001)
                    args = comm[1:]
                    comm = comm[0]
                    match comm:
                        case "force_reload":
                            self.force_reload(*args)
                        case "lazy_reload":
                            self.lazy_reload(*args)
                        case "pause":
                            self.pause_video(*args)
                        case "resume":
                            self.resume_video(*args)
                        case "switch_to_camera":
                            self.switch_to_camera(*args)
                        case "load_video":
                            self.load_video(*args)

            except Empty:
                pass

            if self.file_video:
                img = self.video_player.take_screenshot()
            else:
                if self.camera is None:
                    self.camera = Camera()
                img = self.camera.take_screenshot()
            for i in self.outputs:
                i.put(img)

            sleep(0.02)


        if self.video_player is not None:
            self.video_player.graceful_exit()

        self.camera.disable()

    def force_reload(self, selected: str):
        if self.camera is None:
            self.camera = Camera()

        self.camera.force_reload(selected)

    def lazy_reload(self, selected: str):
        if self.camera is None:
            self.camera = Camera()

        self.camera.lazy_reload(selected)

    def pause_video(self):
        if self.video_player is None:
            return

        self.video_player.pause()

    def resume_video(self):
        if self.video_player is None:
            return

        self.video_player.unpause()

    def switch_to_camera(self):
        self.camera.enable()

        self.file_video = False

        if self.video_player is not None:
            self.video_player.graceful_exit()

        self.video_player = None

    def load_video(self, filename: str):
        self.file = filename
        if self.video_player is not None:
            self.video_player.graceful_exit()

        self.video_player = FileVideoStream(self.file)
        self.file_video = True
        self.camera.disable()

    def graceful_exit(self):
        self.stopped.set()
        self.proc.join()
