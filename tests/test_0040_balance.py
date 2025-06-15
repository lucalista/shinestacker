import sys
sys.path.append('../')
from focus_stack.framework import TqdmCallbacks
from focus_stack.stack_framework import StackJob, CombinedActions 
from focus_stack import (BalanceFrames, BALANCE_RGB, BALANCE_MATCH_HIST, BALANCE_LUMI,
                         BALANCE_LINEAR, BALANCE_GAMMA, BALANCE_HSV, BALANCE_HLS)


def test_tif_rgb_match():
    try:
        job = StackJob("job", "./", input_path="input/img-tif", callbacks=TqdmCallbacks.callbacks)
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=BALANCE_RGB,
                                                      corr_map=BALANCE_MATCH_HIST, plot_histograms=True)],
                                       output_path="output/img-tif-balance-rgb-match"))
        job.run()
    except Exception:
        assert False


def test_jpg_lumi():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg", callbacks=TqdmCallbacks.callbacks)
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=BALANCE_LUMI,
                                                      corr_map=BALANCE_LINEAR,
                                                      plot_histograms=True)],
                                       output_path="output/img-jpg-balance-lumi"))
        job.run()
    except Exception:
        assert False


def test_tif_lumi():
    try:
        job = StackJob("job", "./", input_path="input/img-tif", callbacks=TqdmCallbacks.callbacks)
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=BALANCE_LUMI,
                                                      corr_map=BALANCE_GAMMA,
                                                      plot_histograms=True)],
                                       output_path="output/img-tif-balance-lumi"))
        job.run()
    except Exception:
        assert False


def test_jpg_rgb():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg", callbacks=TqdmCallbacks.callbacks)
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=BALANCE_RGB,
                                                      corr_map=BALANCE_LINEAR,
                                                      plot_histograms=True)],
                                       output_path="output/img-jpg-balance-rgb"))
        job.run()
    except Exception:
        assert False


def test_jpg_hsv():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg", callbacks=TqdmCallbacks.callbacks)
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=BALANCE_HSV,
                                                      corr_map=BALANCE_LINEAR,
                                                      plot_histograms=True)],
                                       output_path="output/img-jpg-balance-sv"))
        job.run()
    except Exception:
        assert False


def test_jpg_hls():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg", callbacks=TqdmCallbacks.callbacks)
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=BALANCE_HLS,
                                                      corr_map=BALANCE_GAMMA,
                                                      plot_histograms=True)],
                                       output_path="output/img-jpg-balance-ls"))
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
