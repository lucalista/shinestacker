import sys
sys.path.append('../')
from focus_stack import StackJob, Actions, Vignetting


def test_vignetting():
    try:
        job = StackJob("job", "./", input_path="input/img-vignetted")
        job.add_action(Actions("vignette",
                               [Vignetting(plot_histograms=True)],
                               output_path="output/img-vignetting"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_vignetting()
