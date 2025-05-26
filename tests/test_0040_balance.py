import sys
sys.path.append('../')
from focus_stack import StackJob, Actions, BalanceFrames, RGB, MATCH_HIST, LUMI, LINEAR, GAMMA, HSV, HLS


def test_tif_rgb_match():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(Actions("balance", output_path="output/img-tif-balance-rgb-match",
                               actions=[BalanceFrames(channel=RGB,
                                                      corr_map=MATCH_HIST, plot_histograms=True)]))
        job.run()
    except Exception:
        assert False


def test_jpg_lumi():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("balance", output_path="output/img-jpg-balance-lumi",
                               actions=[BalanceFrames(channel=LUMI,
                                                      corr_map=LINEAR, plot_histograms=True)]))
        job.run()
    except Exception:
        assert False


def test_tif_lumi():
    try:
        job = StackJob("job", "./", input_path="input/img-tif")
        job.add_action(Actions("balance", output_path="output/img-tif-balance-lumi",
                               actions=[BalanceFrames(channel=LUMI,
                                                      corr_map=GAMMA, plot_histograms=True)]))
        job.run()
    except Exception:
        assert False


def test_jpg_rgb():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("balance", output_path="output/img-jpg-balance-rgb",
                               actions=[BalanceFrames(channel=RGB,
                                                      corr_map=LINEAR, plot_histograms=True)]))
        job.run()
    except Exception:
        assert False


def test_jpg_hsv():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("balance", output_path="output/img-jpg-balance-sv",
                               actions=[BalanceFrames(channel=HSV,
                                                      corr_map=LINEAR, plot_histograms=True)]))
        job.run()
    except Exception:
        assert False


def test_jpg_hls():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("balance", output_path="output/img-jpg-balance-ls",
                               actions=[BalanceFrames(channel=HLS,
                                                      corr_map=GAMMA, plot_histograms=True)]))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_tif_rgb_match()
    test_jpg_lumi()
    test_tif_lumi()
    test_jpg_rgb()
    test_jpg_hsv()
    test_jpg_hls()
