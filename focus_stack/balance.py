import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.optimize import bisect
from .helper import file_folder
from .helper import check_file_exists

def gamma_lut(gamma):
    gamma_inv = 1.0/gamma
    return np.array([((i/255.0)**gamma_inv)*255 for i in np.arange(0, 256)]).astype("uint8")

def adjust_gamma(image, gamma):
    return cv2.LUT(image, gamma_lut(gamma))

def lumi_ratio(mean_lumi, hist, gamma):
    mean_lumi_gamma=np.average(gamma_lut(gamma), weights=hist.flatten())
    return mean_lumi_gamma/mean_lumi

def img_histo(image, mask_size=1, plot=True):
    height, width, channels = image.shape
    mask = np.zeros(image.shape[:2], dtype="uint8")
    cv2.circle(mask, (width//2,height//2), int(min(width, height)*mask_size/2),  (255, 255, 255), -1)
    hist_lumi = cv2.calcHist([cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)], [0], mask, [256], [0, 256])
    if (plot):
        chans = cv2.split(image)
        colors = ("b", "g", "r")
        fig, axs = plt.subplots(1, 2, figsize=(6, 2), sharey=True)
        axs[0].set_ylabel("# of Pixels")
        axs[1].set_ylabel("# of Pixels")
        axs[0].set_xlabel("pixel luminosity")
        axs[1].set_xlabel("color luminosity")
        axs[0].set_xlim([0, 256])
        axs[1].set_xlim([0, 256])
        axs[0].plot(hist_lumi, color='black')
        for (chan, color) in zip(chans, colors):
            hist_col = cv2.calcHist([chan], [0], mask, [256], [0, 256])
            axs[1].plot(hist_col, color=color)
        plt.show()
    mean_lumi = np.average(list(range(256)), weights=hist_lumi.flatten())
    return mean_lumi, hist_lumi

def img_lumi_balance(filename_1, filename_2, input_path, output_path, mask_size=1, plot=True):
    print('balance '+ filename_2+' -> '+ filename_1 + ": ", end='')
    fname_2 = input_path+"/"+filename_2
    check_file_exists(fname_2)
    image_2 = cv2.imread(fname_2)
    if(filename_1 != filename_2):
        fname_1 = input_path+"/"+filename_1
        check_file_exists(fname_1)
        image_1 = cv2.imread(fname_1)
        mean_lumi_1, hist_1 = img_histo(image_1, mask_size, plot)
        mean_lumi_2, hist_2 = img_histo(image_2, mask_size, plot)
        r = mean_lumi_1/mean_lumi_2
        f = lambda x: lumi_ratio(mean_lumi_2, hist_2, x) - r
        gamma = bisect(f, 0.2, 2)
        image_2 = adjust_gamma(image_2, gamma)
        mean_lumi_2, hist_2 = img_histo(image_2, mask_size, plot)
        print("{:.4f}->{:.4f} ({:+.2%}), gamma = {:.4f} ".format(mean_lumi_1, mean_lumi_2, mean_lumi_1/mean_lumi_2-1, gamma))
    else:
        print("saving file duplicate")
    cv2.imwrite(output_path+"/"+filename_2, image_2)

def lumi_balance(input_path, output_path, ref_index=-1, mask_size=1, plot=False):
    fnames = file_folder(input_path)
    if ref_index==-1: ref = fnames[len(fnames)//2]
    fxnames = fnames
    for f in fxnames:
        img_lumi_balance(ref, f, input_path, output_path, mask_size, plot)