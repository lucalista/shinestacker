import sys
sys.path.append('../')
from focus_stack import StackJob, Actions, Vignetting


def test_vignetting():
    try:
        job = StackJob("job", "./", input_path="input/img-vignetted")
        job.add_action(Actions("vignette", output_path="output/img-vignetting",
                               actions=[Vignetting(plot_histograms=True)]))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_vignetting()
