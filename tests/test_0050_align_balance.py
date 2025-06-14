import sys
sys.path.append('../')
from config.config import config
config.init(DISABLE_TQDM=False)
from focus_stack import StackJob, CombinedActions, AlignFrames, BalanceFrames, BALANCE_GAMMA, BALANCE_HSV, BALANCE_HLS, BALANCE_LUMI, BALANCE_RGB


def test_hls_gamma():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(),
                                        BalanceFrames(channel=BALANCE_HLS,
                                                      corr_map=BALANCE_GAMMA)],
                                       output_path="output/img-jpg-align-balance-ls"))
        job.run()
    except Exception:
        assert False


def test_hsv():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(),
                                        BalanceFrames(channel=BALANCE_HSV)],
                                       output_path="output/img-jpg-align-balance-sv"))
        job.run()
    except Exception:
        assert False


def test_rgb():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(),
                                        BalanceFrames(channel=BALANCE_RGB)],
                                       output_path="output/img-jpg-align-balance-rgb"))
        job.run()
    except Exception:
        assert False


def test_lumi():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(CombinedActions("align",
                                       [AlignFrames(), BalanceFrames(channel=BALANCE_LUMI)],
                                       output_path="output/img-jpg-align-balance-lumi"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_hls_gamma()
    test_hsv()
    test_rgb()
    test_lumi()
