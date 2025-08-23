import matplotlib
matplotlib.use('Agg')
from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.vignetting import Vignetting, correct_vignetting


def test_vignetting_function():
    img = read_img(f"examples/input/img-vignetted/vig-0001.jpg")
    try:
        correct_vignetting(img)
    except Exception:
        assert False


def test_vignetting():
    try:
        job = StackJob("job", "examples", input_path="input/img-vignetted")
        job.add_action(CombinedActions("vignette",
                                       [Vignetting(plot_correction=True, plot_summary=True)],
                                       output_path="output/img-vignetting"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_vignetting()
