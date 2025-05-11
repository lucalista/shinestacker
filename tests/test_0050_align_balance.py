import sys
sys.path.append('../')
from focus_stack import *

def test_hls_gamma():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(Actions("img-jpg-align-balance-ls", actions=[AlignFrames(), 
            BalanceFrames(channel=HLS, corr_map=GAMMA)]))
        job.run()
        assert True
    except:
        assert False
        
def test_hsv():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(Actions("img-jpg-align-balance-sv", actions=[AlignFrames(), 
            BalanceFrames(channel=HSV)]))
        job.run()
        assert True
    except:
        assert False
        
def test_rgb():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(Actions("img-jpg-align-balance-rgb", actions=[AlignFrames(), 
            BalanceFrames(channel=RGB)]))
        job.run()
        assert True
    except:
        assert False
        
def test_lumi():
    try:
        job = StackJob("job", "./", input_path="img-jpg")
        job.add_action(Actions("img-jpg-align-balance-lumi", actions=[AlignFrames(), 
            BalanceFrames(channel=LUMI)]))
        job.run()
        assert True
    except:
        assert False

if __name__ == '__main__':
    test_hls_gamma()
    test_hsv()
    test_rgb()
    test_lumi()