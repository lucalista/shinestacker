from shinestacker.config.constants import constants
from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.balance import BalanceFrames


def test_tif_rgb_match():
    try:
        job = StackJob("job", "examples", input_path="input/img-tif", callbacks='tqdm')
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=constants.BALANCE_RGB,
                                                      corr_map=constants.BALANCE_MATCH_HIST,
                                                      plot_histograms=True, plot_summary=True)],
                                       output_path="output/img-tif-balance-rgb-match"))
        job.run()
    except Exception:
        assert False


def test_jpg_lumi():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=constants.BALANCE_LUMI,
                                                      corr_map=constants.BALANCE_LINEAR,
                                                      plot_histograms=True, plot_summary=True)],
                                       output_path="output/img-jpg-balance-lumi"))
        job.run()
    except Exception:
        assert False


def test_tif_lumi():
    try:
        job = StackJob("job", "examples", input_path="input/img-tif", callbacks='tqdm')
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=constants.BALANCE_LUMI,
                                                      corr_map=constants.BALANCE_GAMMA,
                                                      plot_histograms=True, plot_summary=True)],
                                       output_path="output/img-tif-balance-lumi"))
        job.run()
    except Exception:
        assert False


def test_jpg_rgb():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=constants.BALANCE_RGB,
                                                      corr_map=constants.BALANCE_LINEAR,
                                                      plot_histograms=True, plot_summary=True)],
                                       output_path="output/img-jpg-balance-rgb"))
        job.run()
    except Exception:
        assert False


def test_jpg_hsv():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=constants.BALANCE_HSV,
                                                      corr_map=constants.BALANCE_LINEAR,
                                                      plot_histograms=True, plot_summary=True)],
                                       output_path="output/img-jpg-balance-sv"))
        job.run()
    except Exception:
        assert False


def test_jpg_hls():
    try:
        job = StackJob("job", "examples", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("balance",
                                       [BalanceFrames(channel=constants.BALANCE_HLS,
                                                      corr_map=constants.BALANCE_GAMMA,
                                                      plot_histograms=True, plot_summary=True)],
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
