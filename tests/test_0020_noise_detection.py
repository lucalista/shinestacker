import sys
sys.path.append('../')
from focus_stack import StackJob, NoiseDetection, Actions, MaskNoise


def test_detect():
    try:
        job = StackJob("job", "./", input_path="img-noise")
        job.add_action(NoiseDetection())
        job.run()
    except Exception:
        assert False


def test_correct():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(Actions("img-noise-corr", actions=[MaskNoise()]))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_detect()
    test_correct()
