import sys
sys.path.append('../')
from focus_stack import *

def test_jpg():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(Actions("img-jpg-align", actions=[AlignFrames(plot_matches=True)]))
        job.run()
        assert True
    except:
        assert False

def test_tif():
    try:
        job = StackJob("job", "./", input_path="img-tif")
        job.add_action(Actions("img-tif-align", actions=[AlignFrames()]))
        job.run()
        assert True
    except:
        assert False
        
if __name__ == '__main__':
    test_jpg()
    test_tif()