import sys
sys.path.append('../')
from focus_stack import *

def test_jpg():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(MultiLayer("img-jpg-multilayer", input_path=["img-jpg", "img-jpg-stack"], reverse_order=True))
        job.run()
    except:
        assert False
def test_tif():
    try:
        job = StackJob("job", "./", input_path="img-tif")
        job.add_action(MultiLayer("img-tiff-multilayer", input_path=["img-tif", "img-tif-stack"], reverse_order=True))
        job.run()        
    except:
        assert False

if __name__ == '__main__':
    test_jpg()
    test_tif()