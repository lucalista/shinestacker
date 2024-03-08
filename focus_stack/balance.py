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

def adjust_gamma_rgb(image, gamma):
    chans = cv2.split(image)
    ch_out = []
    for c in range(3):
        ch_out.append(cv2.LUT(chans[c], gamma_lut(gamma[c])))
    return cv2.merge(ch_out)

def lumi_expect(hist, gamma, i_min=0, i_max=255):
    return np.average(gamma_lut(gamma)[i_min:i_max+1], weights=hist.flatten()[i_min:i_max+1])

def img_histo(image, mask_size=1, i_min=0, i_max=255, plot=True,):
    height, width, channels = image.shape
    mask = np.zeros(image.shape[:2], dtype="uint8")
    cv2.circle(mask, (width//2,height//2), int(min(width, height)*mask_size/2),  (255, 255, 255), -1)
    hist_lumi = cv2.calcHist([cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)], [0], mask, [256], [0, 256])
    if (plot):
        chans = cv2.split(image)
        colors = ("r", "g", "b")
        fig, axs = plt.subplots(1, 2, figsize=(6, 2), sharey=True)
        for i in range(2):
            axs[i].set_ylabel("# of Pixels")
            axs[i].set_yscale('log')
            axs[i].set_xlim([0, 256])
        axs[0].set_xlabel("pixel luminosity")
        axs[1].set_xlabel("r,g,b luminosity")
        axs[0].plot(hist_lumi, color='black')
        for (chan, color) in zip(chans, colors):
            hist_col = cv2.calcHist([chan], [0], mask, [256], [0, 256])
            axs[1].plot(hist_col, color=color)
        plt.show()
    mean_lumi = np.average(list(range(256))[i_min:i_max+1], weights=hist_lumi.flatten()[i_min:i_max+1])
    return mean_lumi, hist_lumi

def img_lumi_balance(filename_1, filename_2, input_path, output_path, mask_size=1, i_min=0, i_max=255, plot=True):
    print('balance '+ filename_2+' -> '+ filename_1 + ": ", end='')
    fname_2 = input_path+"/"+filename_2
    check_file_exists(fname_2)
    image_2 = cv2.imread(fname_2)
    if(filename_1 != filename_2):
        fname_1 = input_path+"/"+filename_1
        check_file_exists(fname_1)
        image_1 = cv2.imread(fname_1)
        mean_lumi_1, hist_1 = img_histo(image_1, mask_size, i_min, i_max, plot)
        mean_lumi_2, hist_2 = img_histo(image_2, mask_size, i_min, i_max, plot)
        f = lambda x: lumi_expect(hist_2, x, i_min, i_max) - mean_lumi_1
        gamma = bisect(f, 0.1, 5)
        image_2 = adjust_gamma(image_2, gamma)
        mean_lumi_2, hist_2 = img_histo(image_2, mask_size, i_min, i_max, plot)
        print("{:.4f}->{:.4f} ({:+.2%}), gamma = {:.4f} ".format(mean_lumi_1, mean_lumi_2, 1-mean_lumi_1/mean_lumi_2, gamma))
    else:
        print("saving file duplicate")
    cv2.imwrite(output_path+"/"+filename_2, image_2)
    
def img_histo_rgb(image, mask_size=1, i_min=0, i_max=255, plot=True):
    height, width, channels = image.shape
    mask = np.zeros(image.shape[:2], dtype="uint8")
    cv2.circle(mask, (width//2,height//2), int(min(width, height)*mask_size/2),  (255, 255, 255), -1)
    hist_rgb = []
    mean_ch = []
    chans = cv2.split(image)
    colors = ("r", "g", "b")
    if plot:
        fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
        print('')
    c = 0
    for (chan, color) in zip(chans, colors):
        hist_rgb.append(cv2.calcHist([chan], [0], mask, [256], [0, 256]))
        mean_ch.append(np.average(list(range(256))[i_min:i_max+1], weights=hist_rgb[c].flatten()[i_min:i_max+1]))
        if plot:
            axs[c].set_ylabel("# of Pixels")
            axs[c].set_xlabel("pixel luminosity")
            axs[c].set_xlabel(color+" luminosity")
            axs[c].set_xlim([0, 256])
            axs[c].set_yscale('log')
            axs[c].plot(hist_rgb[c], color=color)
            print('mean, '+color+': {:.4f}'.format(mean_ch[c]))
        c += 1
    if plot:
        plt.show()
    return mean_ch, hist_rgb

def img_lumi_balance_rgb(filename_1, filename_2, input_path, output_path, mask_size=1, i_min=0, i_max=255, plot=True):
    print('balance '+ filename_2+' -> '+ filename_1 + ": ", end='')
    fname_2 = input_path+"/"+filename_2
    check_file_exists(fname_2)
    image_2 = cv2.imread(fname_2)
    if(filename_1 != filename_2):
        fname_1 = input_path+"/"+filename_1
        check_file_exists(fname_1)
        image_1 = cv2.imread(fname_1)
        mean_ch_1, hist_rgb_1 = img_histo_rgb(image_1, mask_size, i_min, i_max, plot)
        mean_ch_2, hist_rgb_2= img_histo_rgb(image_2, mask_size, i_min, i_max, plot)
        gamma = []
        for c in range(3):
            f = lambda x: lumi_expect(hist_rgb_2[c], x, i_min, i_max) - mean_ch_1[c]
            gamma.append(bisect(f, 0.1, 5))
        image_2 = adjust_gamma_rgb(image_2, gamma)
        mean_ch_2, hist_rgb_2 = img_histo_rgb(image_2, mask_size, i_min, i_max, plot)
        for c in range(3):
            print("{:.4f}->{:.4f} ({:+.2%}), gamma = {:.4f} ".format(mean_ch_1[c], mean_ch_2[c], 1-mean_ch_1[c]/mean_ch_2[c], gamma[c]))
    else:
        print("saving file duplicate")
    cv2.imwrite(output_path+"/"+filename_2, image_2)

def lumi_balance(input_path, output_path, ref_index=-1, mask_size=1, i_min=0, i_max=255, plot=False):
    fnames = file_folder(input_path)
    if ref_index==-1: ref = fnames[len(fnames)//2]
    fxnames = fnames
    for f in fxnames:
        img_lumi_balance(ref, f, input_path, output_path, mask_size, i_min, i_max, plot)
        
def lumi_balance_rgb(input_path, output_path, ref_index=-1, mask_size=1, i_min=0, i_max=255, plot=False):
    fnames = file_folder(input_path)
    if ref_index==-1: ref = fnames[len(fnames)//2]
    fxnames = fnames
    for f in fxnames:
        img_lumi_balance_rgb(ref, f, input_path, output_path, mask_size, i_min, i_max, plot)