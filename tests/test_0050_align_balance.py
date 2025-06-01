import sys
sys.path.append('../')
from focus_stack import StackJob, Actions, AlignFrames, BalanceFrames, BALANCE_GAMMA, BALANCE_HSV, BALANCE_HLS, BALANCE_LUMI, BALANCE_RGB


def test_hls_gamma():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("align", output_path="output/img-jpg-align-balance-ls",
                               actions=[AlignFrames(), BalanceFrames(channel=BALANCE_HLS, corr_map=BALANCE_GAMMA)]))
        job.run()
    except Exception:
        assert False


def test_hsv():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("align", output_path="output/img-jpg-align-balance-sv",
                               actions=[AlignFrames(), BalanceFrames(channel=BALANCE_HSV)]))
        job.run()
    except Exception:
        assert False


def test_rgb():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("align", output_path="output/img-jpg-align-balance-rgb",
                               actions=[AlignFrames(), BalanceFrames(channel=BALANCE_RGB)]))
        job.run()
    except Exception:
        assert False


def test_lumi():
    try:
        job = StackJob("job", "./", input_path="input/img-jpg")
        job.add_action(Actions("align", output_path="output/img-jpg-align-balance-lumi",
                               actions=[AlignFrames(), BalanceFrames(channel=BALANCE_LUMI)]))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_hls_gamma()
    test_hsv()
    test_rgb()
    test_lumi()
