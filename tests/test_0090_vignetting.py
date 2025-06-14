import sys
sys.path.append('../')
from config.config import config
config.init(DISABLE_TQDM=False)
from focus_stack import StackJob, CombinedActions, Vignetting


def test_vignetting():
    try:
        job = StackJob("job", "./", input_path="input/img-vignetted")
        job.add_action(CombinedActions("vignette",
                                       [Vignetting(plot_histograms=True)],
                                       output_path="output/img-vignetting"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_vignetting()
