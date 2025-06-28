import sys
sys.path.append('../')
from config.constants import constants
from algorithms.stack_framework import StackJob, CombinedActions
from algorithms.align import AlignFrames
from algorithms.balance import BalanceFrames


def test_hls_gamma():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(),
                                        BalanceFrames(channel=constants.BALANCE_HLS,
                                                      corr_map=constants.BALANCE_GAMMA)],
                                       output_path="output/img-jpg-align-balance-ls"))
        job.run()
    except Exception:
        assert False


def test_hsv():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(),
                                        BalanceFrames(channel=constants.BALANCE_HSV)],
                                       output_path="output/img-jpg-align-balance-sv"))
        job.run()
    except Exception:
        assert False


def test_rgb():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(),
                                        BalanceFrames(channel=constants.BALANCE_RGB)],
                                       output_path="output/img-jpg-align-balance-rgb"))
        job.run()
    except Exception:
        assert False


def test_lumi():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(), BalanceFrames(channel=constants.BALANCE_LUMI)],
                                       output_path="output/img-jpg-align-balance-lumi"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_hls_gamma()
    test_hsv()
    test_rgb()
    test_lumi()
