import matplotlib.pyplot as plt
import cv2
import numpy as np
from focus_stack.stack_framework import FramesRefActions
from termcolor import colored, cprint
    
class AlignLayers(FramesRefActions):
    ALIGN_HOMOGRAPHY = "homography"
    ALIGN_RIGID = "rigid"
    def __init__(self, wdir, name, input_path, output_path='', step_align=True, ref_idx=-1, detector='SIFT', descriptor='SIFT', match_method='KNN', flann_idx_kdtree=2, flann_trees=5, flann_checks=50, match_threshold=0.75, method=ALIGN_RIGID, rans_threshold=5.0, plot_matches=False):
        FramesRefActions.__init__(self, wdir, name, input_path, output_path, ref_idx, step_align)
        self.detector = detector
        self.descriptor = descriptor
        self.match_method = match_method
        self.flann_idx_kdtree = flann_idx_kdtree
        self.flann_trees = flann_trees
        self.flann_checks = flann_checks
        self.match_threshold = match_threshold
        self.method = method
        self.min_matches = 4 if self.method==AlignLayers.ALIGN_HOMOGRAPHY else 3
        self.rans_threshold = rans_threshold
        self.plot_matches = plot_matches
    def run_frame(self, idx, ref_idx):
        print("aligning frame: {}, file: {}                    ".format(self.count, self.filenames[idx]), end='\r')
        self.align_images(ref_idx, idx)
    def create_detector(self):
        detector = None
        if self.detector=='SIFT': detector = cv2.SIFT_create()
        elif self.detector=='ORB': detector = cv2.ORB_create()
        elif self.detector=='SURF': detector = cv2.FastFeatureDetector_create()
        elif self.detector=='AKAZE': detector = cv2.AKAZE_create()
        assert(detector), "Invalid detector: " + self.detector_method
        return detector
    def create_descriptor(self):
        descriptor = None
        if self.descriptor=='ORB': descriptor = cv2.SIFT_create()
        elif self.descriptor=='SIFT': descriptor = cv2.ORB_create()
        elif self.descriptor=='AKAZE': descriptor = cv2.AKAZE_create()
        assert(descriptor), "Invalid descriptor: " + self.detector_method
        return descriptor
    def detect_and_compute(self, detector, descriptor, img_bw_0, img_bw_1):
        if self.detector==self.descriptor and (self.detector=='SIFT' or self.detector=='AKAZE'):
            kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
            kp_1, des_1 = detector.detectAndCompute(img_bw_1, None)
        else:
            kp_0 = detector.detect(img_bw_0, None)
            kp_1 = detector.detect(img_bw_1, None)
            kp_0, des_0 = descriptor.compute(img_bw_0, kp_0)
            kp_1, des_1 = descriptor.compute(img_bw_1, kp_1)
        return kp_0, kp_1, des_0, des_1
    def get_good_matches(self, des_0, des_1):
        if self.match_method=='KNN':
            flann = cv2.FlannBasedMatcher(dict(algorithm=self.flann_idx_kdtree, trees=self.flann_trees), dict(checks=self.flann_checks))
            matches = flann.knnMatch(des_0, des_1, k=2)
            good_matches = []
            for m, n in matches:
                if m.distance < self.match_threshold*n.distance:
                    good_matches.append(m)
        elif self.match_method=='NORM_HAMMING':
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            good_matches = bf.match(des_0, des_1)
            good_matches = sorted(good_matches, key=lambda x: x.distance)
        return good_matches
    def find_transform(self, src_pts, dst_pts):
        if self.method==AlignLayers.ALIGN_HOMOGRAPHY:
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, self.rans_threshold)
        elif self.method==AlignLayers.ALIGN_RIGID:
            M, mask = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=self.rans_threshold)
        else:
            assert(false), "invalid align method: " + self.method
        return M, mask        
    def align_images(self, ref_idx, idx):
        filename_ref, filename_0 = self.filenames[ref_idx], self.filenames[idx]
        img_0 = cv2.imread(self.input_dir + "/" + filename_0)
        if img_0 is None: raise Exception("Invalid file: " + self.input_dir + "/" + filename_0)
        if filename_0 == filename_ref:
            cv2.imwrite(self.output_dir + "/" + filename_0, img_0, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
            if(self.plot_matches):
                print('')
                print("reference image unchanged")
            return
        img_ref = cv2.imread((self.output_dir if self.step_process else self.input_dir)  + "/" + filename_ref)
        if img_ref is None: raise Exception("Invalid file: " + self.input_dir + "/" + filename_ref)    
        img_bw_0 = cv2.cvtColor(img_0, cv2.COLOR_BGR2GRAY)
        img_bw_1 = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY)
        detector = self.create_detector()
        descriptor = self.create_descriptor()
        kp_0, kp_1, des_0, des_1 = self.detect_and_compute(detector, descriptor, img_bw_0, img_bw_1)
        good_matches = self.get_good_matches(des_0, des_1)
        #if verbose: print("matches: {} ".format(len(good_matches)))
        n_good_matches = len(good_matches)
        self.n_matches[idx] = n_good_matches
        if n_good_matches >= self.min_matches:
            src_pts = np.float32([kp_0[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, mask = self.find_transform(src_pts, dst_pts)
            if(self.plot_matches): matches_mask = mask.ravel().tolist()
            h, w = img_bw_1.shape
            pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0] ]).reshape(-1, 1 ,2)
            if self.method==AlignLayers.ALIGN_HOMOGRAPHY:
                dst = cv2.perspectiveTransform(pts, M)
                img_warp = cv2.warpPerspective(img_0, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
            elif self.method==AlignLayers.ALIGN_RIGID:
                img_warp = cv2.warpAffine(img_0, M, (img_0.shape[1], img_0.shape[0]))
            cv2.imwrite(self.output_dir + "/" + filename_0, img_warp, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        else:
            img_warp = None
            if(self.plot_matches): matches_mask = None
            cprint("image " + filename_0 + " not aligned, too few matches found: {}         ".format(n_good_matches), "red")
        if(self.plot_matches):
            draw_params = dict(matchColor = (0,255,0), singlePointColor=None, matchesMask=matches_mask, flags = 2)
            img_match = cv2.cvtColor(cv2.drawMatches(img_0, kp_0, img_ref, kp_1, good_matches, None, **draw_params), cv2.COLOR_BGR2RGB)
            print('')
            print("matches: {}".format(n_good_matches))
            plt.figure(figsize=(10, 5))
            plt.imshow(img_match, 'gray'),
            plt.show()
    def begin(self):
        FramesRefActions.begin(self)
        self.n_matches = np.zeros(self.counts)
    def end(self):
        print("                                 ")
        plt.figure(figsize=(10, 5))
        x = np.arange(1, len(self.n_matches) + 1, dtype=int)
        no_ref = (x != self.ref_idx + 1)
        x = x[no_ref]
        y = self.n_matches[no_ref]
        plt.plot([self.ref_idx + 1, self.ref_idx + 1], [0, y.max()], color='cornflowerblue', linestyle='--', label='reference frame')
        plt.plot([x[0], x[-1]], [self.min_matches, self.min_matches], color='lightgray', linestyle='--', label='min. matches')
        plt.plot(x, y, color='navy', label='matches')
        plt.xlabel('frame')
        plt.ylabel('n. of matches')
        plt.legend()
        plt.ylim(0)
        plt.xlim(x[0], x[-1])
        plt.show()
