import matplotlib
matplotlib.use('Agg')
from shinestacker.algorithms.stack_framework import StackJob, CombinedActions
from shinestacker.algorithms.vignetting import Vignetting


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
