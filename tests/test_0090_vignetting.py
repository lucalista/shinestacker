import sys
sys.path.append('../')
from focus_stack import StackJob, Actions, Vignetting


def test_vignetting():
    try:
        job = StackJob("job", "./", input_path="img-vignetted")
        job.add_action(Actions("img-vignetting", actions=[Vignetting()]))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_vignetting()
