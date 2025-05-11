import sys
sys.path.append('../')
from focus_stack import *

def test_run():
    try:
        job = StackJob("job", "./")
        job.add_action(NoiseDetection("noise-map", input_path=["img-noise"]))
        job.run()
        assert True
    except:
        assert False

if __name__ == '__main__':
    test_run()

