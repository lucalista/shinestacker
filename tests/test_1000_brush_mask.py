import sys
sys.path.append('../')
import numpy as np
from gui.brush_preview import brush_profile


def test_brush_profile():
    r = np.linspace(0.0, 1.5, 100)
    for hardness in np.linspace(0.0, 1.0, 20):
        mask = brush_profile(r, hardness)
        assert mask.min() >= 0.0 and mask.max() <= 1.0


if __name__ == '__main__':
    test_brush_profile()
    
