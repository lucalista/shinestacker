import sys
sys.path.append('../')
from focus_stack import *

def test_jpg():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(FocusStack("img-jpg-stack", PyramidStack(), postfix='_pyr'))
        job.run()
    except:
        assert False
        
def test_tif():
    try:
        job = StackJob("job", "./", input_path="img-tif")
        job.add_action(FocusStack("img-tif-stack", PyramidStack(), postfix='_pyr'))
        job.run()
    except:
        assert False
        
def test_jpg_dm():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(FocusStack("img-jpg-stack", DepthMapStack(), postfix='_dm'))
        job.run()
    except:
        assert False
        
def test_bunches():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(FocusStackBunch("img-jpg-bunches",  PyramidStack(), frames=3))
        job.run()
    except:
        assert False

if __name__ == '__main__':
    test_jpg()
    test_tif()
    test_jpg_dm()
    test_bunches()