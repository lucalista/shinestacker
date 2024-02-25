import matplotlib.pyplot as plt
import cv2
import numpy as np
from .helper import file_folder

def img_align(filename_ref, filename_0, ref_path, input_path, align_path, detector_method='SIFT',  descriptor_method='SIFT', match_method='KNN', flann_idx_kdtree=0, match_threshold=0.7, plot=False):
    print('align '+ filename_0+' -> '+ filename_ref + ": ", end='')
    img_0 = cv2.imread(input_path+"/"+filename_0)
    if img_0 is None: raise Exception("Invalid file: " + input_path+"/"+filename_0)
    if filename_0 == filename_ref:
        print("saving file duplicate")
        cv2.imwrite(align_path+"/"+filename_0, img_0)
        return
    img_ref = cv2.imread(ref_path+"/"+filename_ref)
    if img_ref is None: raise Exception("Invalid file: " + input_path+"/"+filename_ref)    
    img_bw_0 = cv2.cvtColor(img_0, cv2.COLOR_BGR2GRAY)
    img_bw_1 = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY)
    if detector_method=='SIFT': detector = cv2.SIFT_create()
    elif detector_method=='ORB': detector = cv2.ORB_create()
    elif detector_method=='SURF': detector = cv2.FastFeatureDetector_create()
    elif detector_method=='AKAZE': detector = cv2.AKAZE_create()
    if descriptor_method=='ORB': descriptor = cv2.SIFT_create()
    elif descriptor_method=='SIFT': descriptor = cv2.ORB_create()
    elif descriptor_method=='AKAZE': descriptor = cv2.AKAZE_create()
    if detector_method==descriptor_method and (detector_method=='SIFT' or detector_method=='AKAZE'):
        kp_0, des_0 = detector.detectAndCompute(img_bw_0, None)
        kp_1, des_1 = detector.detectAndCompute(img_bw_1, None)
    else:
        kp_0 = detector.detect(img_bw_0, None)
        kp_1 = detector.detect(img_bw_1, None)
        kp_0, des_0 = descriptor.compute(img_bw_0, kp_0)
        kp_1, des_1 = descriptor.compute(img_bw_1, kp_1)
    if match_method=='KNN':
        index_params = dict(algorithm = flann_idx_kdtree, trees = 5)
        search_params = dict(checks = 50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des_0, des_1, k=2)
        good = []
        for m, n in matches:
            if m.distance < match_threshold*n.distance:
                good.append(m)
    elif match_method=='NORM_HAMMING':
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        good = bf.match(des_0, des_1)
        good = sorted(good, key=lambda x: x.distance)
    print("matches: {} ".format(len(good)))
    MIN_MATCH_COUNT = 4
    if len(good) > MIN_MATCH_COUNT:
        src_pts = np.float32([kp_0[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_1[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)
        matchesMask = mask.ravel().tolist()
        h, w = img_bw_1.shape
        pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0] ]).reshape(-1, 1 ,2)
        dst = cv2.perspectiveTransform(pts, M)
        img_warp = cv2.warpPerspective(img_0, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    else:
        print("Not enough matches are found - {}/{}".format(len(good), MIN_MATCH_COUNT))
        matchesMask = None
    if(plot):
        draw_params = dict(matchColor = (0,255,0), singlePointColor = None, matchesMask = matchesMask, flags = 2)
        img_match = cv2.drawMatches(img_0, kp_0, img_ref, kp_1, good, None, **draw_params)
        plt.figure(figsize=(20, 10))
        plt.imshow(img_match, 'gray'),
    plt.show()
    cv2.imwrite(align_path+"/"+filename_0, img_warp)
    
def align_frames(input_path, align_path, step_align=True, ref_idx=-1, detector_method='SIFT', descriptor_method='SIFT', match_method='KNN', flann_idx_kdtree=0, match_threshold=0.7, plot=False):
    fnames = file_folder(input_path)
    if ref_idx == -1: ref_idx = len(fnames)//2
    fname_ref = fnames[ref_idx]
    img_align(fname_ref, fname_ref, input_path, input_path, align_path, detector_method, descriptor_method, match_method, flann_idx_kdtree, match_threshold, plot)
    ref_path = align_path if step_align else input_path
    def align_range(ref_idx, rng):
        fname_ref = fnames[ref_idx]
        for i in rng:
            fname = fnames[i]
            img_align(fname_ref, fname, ref_path, input_path, align_path, detector_method, descriptor_method, match_method, flann_idx_kdtree, match_threshold, plot)
            fname_ref=fname
    align_range(ref_idx, range(ref_idx+1, len(fnames)+1))
    align_range(ref_idx, range(ref_idx-1, -1, -1))    