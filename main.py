from multiprocessing import Manager
from VideoReader import VideoSource
from Processors import ScaleFilter, InvertFilter, MirrorFilter, GrayscaleFilter
from App import App

if __name__ == "__main__":
    manager = Manager()

    app = App(manager)

    scale = ScaleFilter(outputs = [app.sinkPipe], manager=manager)
    invert = InvertFilter(outputs = [scale.input], manager=manager)
    mirror = MirrorFilter(outputs = [invert.input], manager=manager)
    gray = GrayscaleFilter(outputs = [mirror.input], manager=manager)

    source = VideoSource(app.instructions, outputs = [gray.input, app.sourcePipe])

    app.run()

    for i in [source, gray, mirror, invert, scale]:
        i.graceful_exit()
    
