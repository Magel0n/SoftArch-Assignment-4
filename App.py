from time import sleep
from multiprocessing import Manager

import tkinter.filedialog
import tkinter as tk
from queue import Empty

from PIL import ImageTk, Image

from cv2_enumerate_cameras import enumerate_cameras

default_image = Image.new("RGB", (480, 360))


class App:
    def __init__(self, manager: Manager):
        self.window = tk.Tk()

        self.window.title("Video Filter App")
        self.window.resizable(width=False, height=False)

        self.sourcePipe = manager.Queue()
        self.sinkPipe = manager.Queue()
        self.instructions = manager.Queue()

        self.controlPanelCamera = tk.Frame(master=self.window)
        self.select_video = tk.Button(
            master=self.controlPanelCamera,
            text="Play a video",
            command=self.switch_to_video,
        )

        self.selected_camera = tk.StringVar(self.controlPanelCamera)
        self.camMenu = tk.OptionMenu(self.controlPanelCamera, self.selected_camera, "")

        self.reload_button = tk.Button(
            self.controlPanelCamera,
            text="Reload Camera",
            command=lambda: self.instructions.put(("force_reload", self.selected_camera.get())),
        )

        self.select_video.grid(row=0, column=0)
        self.camMenu.grid(row=0, column=1, padx=30, pady=10)
        self.reload_button.grid(row=0, column=2)

        self.file = ""
        self.controlPanelVideo = tk.Frame(master=self.window)
        self.select_video = tk.Button(
            master=self.controlPanelVideo,
            text="Change the video",
            command=self.switch_to_video,
        )
        self.pause = tk.Button(
            master=self.controlPanelVideo, text="Pause", command=self.pause_video
        )
        self.reset = tk.Button(
            master=self.controlPanelVideo, text="Reset", command=self.reset_video
        )
        self.camera_switch = tk.Button(
            master=self.controlPanelVideo,
            text="Switch back to camera",
            command=self.switch_to_camera,
        )

        self.select_video.grid(row=0, column=0, padx=15, pady=10)
        self.pause.grid(row=0, column=1, padx=15, pady=10)
        self.reset.grid(row=0, column=2, padx=15, pady=10)
        self.camera_switch.grid(row=0, column=3, padx=15, pady=10)

        self.displays_box = tk.Frame(master=self.window)
        self.video_filters = []
        self.image_labels = []

        self.image_labels.append(self.make_video_box("Source", 0, 0))
        self.image_labels.append(self.make_video_box("Sink", 0, 1))

        self.displays_box.pack()
        self.controlPanelCamera.pack()

        self.window.protocol("WM_DELETE_WINDOW", self.graceful_exit)
        self.job = None

    def run(self):
        self.camMenu["menu"].delete(0, "end")

        actual_cameras = set([i.name for i in enumerate_cameras()])
        for i in actual_cameras:
            self.camMenu["menu"].add_command(
                label=i, command=lambda x=i: self.selected_camera.set(x)
            )
        self.selected_camera.set(list(actual_cameras)[0])

        self.job = self.window.after(20, self.update_app_forever)
        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self.graceful_exit()

    def make_video_box(self, name: str, row: int = 0, column: int = 0):
        box = tk.Frame(master=self.displays_box, relief=tk.GROOVE)
        image = ImageTk.PhotoImage(default_image, master=box)

        video = tk.Label(master=box, image=image)
        video.image = image
        label = tk.Label(text=name, master=box, font=("Arial", 20))

        box.grid(row=row, column=column, padx=10, pady=10)

        video.pack()
        label.pack()

        return video

    def pause_video(self):
        self.instructions.put(("pause",))
        self.pause.configure(text="Resume", command=self.resume_video)

    def resume_video(self):
        self.instructions.put(("resume",))
        self.pause.configure(text="Pause", command=self.pause_video)

    def reset_video(self):
        if self.file != "":
            self.instructions.put(("load_video", self.file))

    def switch_to_camera(self):
        self.instructions.put(("switch_to_camera",))
        self.controlPanelCamera.pack()
        self.controlPanelVideo.pack_forget()

    def switch_to_video(self):
        self.file = tkinter.filedialog.askopenfilename()
        if self.file != "":
            self.instructions.put(("load_video", self.file))
            self.controlPanelCamera.pack_forget()
            self.controlPanelVideo.pack()

    def update_app_forever(self):
        cur_cameras = []
        last = self.camMenu["menu"].index("end")
        for i in range(last + 1):
            self.camMenu["menu"].entrycget(i, "label")
            cur_cameras.append(self.camMenu["menu"].entrycget(i, "label"))

        actual_cameras = {i.name for i in enumerate_cameras()}

        if set(cur_cameras) != actual_cameras:
            self.camMenu["menu"].delete(0, "end")
            for i in actual_cameras:
                self.camMenu["menu"].add_command(
                    label=i, command=lambda x=i: self.selected_camera.set(x)
                )

        self.instructions.put(("lazy_reload", self.selected_camera.get()))

        try:
            img = ImageTk.PhotoImage(self.sourcePipe.get(timeout=0.2))
            self.image_labels[0].configure(image=img)
            self.image_labels[0].image = img
        except Empty:
            pass

        try:
            img = ImageTk.PhotoImage(self.sinkPipe.get(timeout=0.2))
            self.image_labels[1].configure(image=img)
            self.image_labels[1].image = img
        except Empty:
            pass

        self.job = self.window.after(1, self.update_app_forever)

    def graceful_exit(self):
        self.window.after_cancel(self.job)
        sleep(0.1)

        self.window.destroy()
