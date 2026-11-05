# pylint: disable=C0415, W0718
"""Optional OpenCL implementation of SIFT feature extraction, based on silx.

It returns the same objects as cv2.SIFT.detectAndCompute (cv2.KeyPoint list and
float32 descriptors), so matching and transform estimation are unchanged.
Needs an OpenCL driver (GPU, or a CPU runtime); without one OpenCV SIFT is used.
"""
import atexit
import importlib
import importlib.util
import threading
import weakref
import numpy as np
import cv2

_probe = {}
_all_plans = weakref.WeakSet()
_atexit_registered = []


def _probe_device():
    """Look for OpenCL devices once; importing silx scans the OpenCL platforms."""
    if not _probe:
        try:
            ocl = importlib.import_module('silx.opencl').ocl
            importlib.import_module('silx.opencl.sift')
            devices = [d for p in ocl.platforms for d in p.devices] if ocl else []
            _probe.update(usable=bool(devices), has_gpu=any(d.type == 'GPU' for d in devices))
        except Exception:
            _probe.update(usable=False, has_gpu=False)
    return _probe


def silx_installed():
    """Whether the opencl extra is installed; unlike silx_sift_usable() it does not import silx."""
    return all(importlib.util.find_spec(m) is not None for m in ('silx', 'pyopencl'))


def silx_sift_usable():
    return _probe_device()['usable']


def _devicetype():
    return 'GPU' if _probe_device()['has_gpu'] else 'ALL'


def device_name():
    """Name of the OpenCL device the plans run on.

    silx caches the context, so the plans get the same one (PYOPENCL_CTX is honoured)."""
    ocl = importlib.import_module('silx.opencl').ocl
    return ocl.create_context(devicetype=_devicetype()).devices[0].name.strip()


def _free_all_plans():
    # free the OpenCL buffers before the interpreter tears pyopencl down
    for plans in list(_all_plans):
        plans.free_buffers()


class SiftPlans:
    """The OpenCL plans of one feature matcher, one per image shape.

    A plan holds the kernels and buffers (some GB at full resolution). keypoints() is
    serialised inside silx, so a plan is shared by all alignment threads of the matcher.
    The plans are freed with the owner, or earlier by release()."""

    def __init__(self):
        self._plans = {}
        self._lock = threading.Lock()
        _all_plans.add(self)

    def _get_plan(self, shape):
        with self._lock:
            plan = self._plans.get(shape)
            if plan is None:
                from silx.opencl.sift import SiftPlan
                plan = SiftPlan(shape=shape, dtype=np.uint8, devicetype=_devicetype())
                if not _atexit_registered:
                    # registered after pyopencl's own handler, so that it runs before it
                    atexit.register(_free_all_plans)
                    _atexit_registered.append(True)
                self._plans[shape] = plan
            return plan

    def release(self):
        # a plan still used by a thread is freed when its call returns
        with self._lock:
            self._plans.clear()

    def free_buffers(self):
        with self._lock:
            for plan in self._plans.values():
                plan.free_buffers()
            self._plans.clear()

    def detect_and_compute(self, img_bw):
        """SIFT keypoints and descriptors of an 8-bit grayscale image, computed with OpenCL."""
        plan = self._get_plan(img_bw.shape)
        kp_array = plan.keypoints(np.ascontiguousarray(img_bw))
        if len(kp_array) == 0:
            return [], None
        # silx scale is sigma, cv2 size a diameter; silx angle is in radians
        keypoints = [cv2.KeyPoint(float(k.x), float(k.y), float(2 * k.scale),
                                  float(np.degrees(k.angle)) % 360.0)
                     for k in kp_array]
        return keypoints, np.ascontiguousarray(kp_array.desc, dtype=np.float32)
