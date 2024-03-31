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

def adjust_gamma_ch3(image, gamma, ch_range=[0, 1, 2]):
    chans = cv2.split(image)
    ch_out = []
    for c in range(3):
        if c in ch_range:
            ch_out.append(cv2.LUT(chans[c], gamma_lut(gamma[c])))
        else:
            ch_out.append(chans[c])
    return cv2.merge(ch_out)

def lumi_expect(hist, gamma, i_min=0, i_max=255):
    return np.average(gamma_lut(gamma)[i_min:i_max+1], weights=hist.flatten()[i_min:i_max+1])

def lumi_mask(image, mask_radius=-1):
    if mask_radius > 0:
        height, width, channels = image.shape
        mask = np.zeros(image.shape[:2], dtype="uint8")
        cv2.circle(mask, (width//2, height//2), int(min(width, height)*mask_radius/2),  (255, 255, 255), -1)
    else:
        mask = np.full(image.shape[:2], 266, dtype="uint8")
    return mask

def histo_plot(ax, histo, x_label, color):
    ax.set_ylabel("# of Pixels")
    ax.set_xlabel(x_label)
    ax.set_xlim([0, 256])
    ax.set_yscale('log')
    ax.plot(histo, color=color)

def img_histo(image, mask_radius=-1, i_min=0, i_max=255, plot=True):
    mask = lumi_mask(image, mask_radius)
    hist_lumi = cv2.calcHist([cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)], [0], mask, [256], [0, 256])
    if (plot):
        chans = cv2.split(image)
        colors = ("r", "g", "b")
        fig, axs = plt.subplots(1, 2, figsize=(6, 2), sharey=True)
        histo_plot(axs[0], hist_lumi, "pixel luminosity", 'black')
        for (chan, color) in zip(chans, colors):
            hist_col = cv2.calcHist([chan], [0], mask, [256], [0, 256])
            histo_plot(axs[1], hist_col, "r,g,b luminosity", color)
        plt.show()
    mean_lumi = np.average(list(range(256))[i_min:i_max+1], weights=hist_lumi.flatten()[i_min:i_max+1])
    return mean_lumi, hist_lumi

def img_histo_rgb(image, mask_radius=-1, i_min=0, i_max=255, plot=True):
    mask = lumi_mask(image, mask_radius)
    hist_rgb = []
    mean_ch = []
    chans = cv2.split(image)
    colors = ("r", "g", "b")
    if plot:
        fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True, verbose=True)
        if verbose: print('')
    c = 0
    for (chan, color) in zip(chans, colors):
        hist_rgb.append(cv2.calcHist([chan], [0], mask, [256], [0, 256]))
        mean_ch.append(np.average(list(range(256))[i_min:i_max+1], weights=hist_rgb[c].flatten()[i_min:i_max+1]))
        if plot:
            histo_plot(axs[c], hist_rgb[c], color+" luminosity", color)
            if verbose: print('mean, '+color+': {:.4f}'.format(mean_ch[c]))
        c += 1
    if plot:
        plt.show()
    return mean_ch, hist_rgb

def img_histo_hsv(image_hsv, mask_radius=-1, i_min=0, i_max=255, plot=True, verbose=True):
    mask = lumi_mask(image_hsv, mask_radius)
    hist_hsv = []
    mean_ch = []
    chans = cv2.split(image_hsv)
    colors = ("pink", "red", "black")
    if plot:
        fig, axs = plt.subplots(1, 3, figsize=(6, 2), sharey=True)
        if verbose: print('')
    c = 0
    for (chan, color) in zip(chans, colors):
        hist_hsv.append(cv2.calcHist([chan], [0], mask, [256], [0, 256]))
        mean_ch.append(np.average(list(range(256))[i_min:i_max+1], weights=hist_hsv[c].flatten()[i_min:i_max+1]))
        if plot:
            histo_plot(axs[c], hist_hsv[c],"ch luminosity", color)
            if verbose: print('mean, '+color+': {:.4f}'.format(mean_ch[c]))
        c += 1
    if plot:
        plt.show()
    return mean_ch, hist_hsv

def img_lumi_balance(filename_1, filename_2, input_path, output_path, mask_radius=-1, i_min=0, i_max=255, plot=True, verbose=True):
    if verbose: print('balance '+ filename_2+' -> '+ filename_1 + ": ", end='')
    fname_2 = input_path+"/"+filename_2
    check_file_exists(fname_2)
    image_2 = cv2.imread(fname_2)
    if(filename_1 != filename_2):
        fname_1 = input_path+"/"+filename_1
        check_file_exists(fname_1)
        image_1 = cv2.imread(fname_1)
        mean_lumi_1, hist_1 = img_histo(image_1, mask_radius, i_min, i_max, plot)
        mean_lumi_2, hist_2 = img_histo(image_2, mask_radius, i_min, i_max, plot)
        f = lambda x: lumi_expect(hist_2, x, i_min, i_max) - mean_lumi_1
        gamma = bisect(f, 0.1, 5)
        image_2 = adjust_gamma(image_2, gamma)
        mean_lumi_2, hist_2 = img_histo(image_2, mask_radius, i_min, i_max, plot)
        if verbose: print("{:.4f}->{:.4f} ({:+.2%}), gamma = {:.4f} ".format(mean_lumi_1, mean_lumi_2, 1-mean_lumi_1/mean_lumi_2, gamma))
    else:
        if verbose: print("saving file duplicate")
    cv2.imwrite(output_path+"/"+filename_2, image_2, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

def img_lumi_balance_rgb(filename_1, filename_2, input_path, output_path, mask_radius=-1, i_min=0, i_max=255, plot=True, verbose=True):
    if verbose: print('balance '+ filename_2+' -> '+ filename_1)
    fname_2 = input_path+"/"+filename_2
    check_file_exists(fname_2)
    image_2 = cv2.imread(fname_2)
    if(filename_1 != filename_2):
        fname_1 = input_path+"/"+filename_1
        check_file_exists(fname_1)
        image_1 = cv2.imread(fname_1)
        mean_ch_1, hist_rgb_1 = img_histo_rgb(image_1, mask_radius, i_min, i_max, plot)
        mean_ch_2, hist_rgb_2= img_histo_rgb(image_2, mask_radius, i_min, i_max, plot)
        gamma = []
        for c in range(3):
            f = lambda x: lumi_expect(hist_rgb_2[c], x, i_min, i_max) - mean_ch_1[c]
            gamma.append(bisect(f, 0.1, 5))
        image_2 = adjust_gamma_ch3(image_2, gamma)
        mean_ch_2, hist_rgb_2 = img_histo_rgb(image_2, mask_radius, i_min, i_max, plot)
        for c in range(3):
            if verbose: print("{:.4f}->{:.4f} ({:+.2%}), gamma = {:.4f} ".format(mean_ch_1[c], mean_ch_2[c], 1-mean_ch_1[c]/mean_ch_2[c], gamma[c]))
    else:
        if verbose: print("saving file duplicate")
    cv2.imwrite(output_path+"/"+filename_2, image_2, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    
def img_lumi_balance_hsv(filename_1, filename_2, input_path, output_path, mask_radius=-1, i_min=0, i_max=255, plot=True, verbose=True):
    if verbose: print('balance '+ filename_2+' -> '+ filename_1)
    fname_2 = input_path+"/"+filename_2
    check_file_exists(fname_2)
    image_2 = cv2.imread(fname_2)
    image_hsv_2 = cv2.cvtColor(image_2, cv2.COLOR_BGR2HSV)
    if(filename_1 != filename_2):
        fname_1 = input_path+"/"+filename_1
        check_file_exists(fname_1)
        image_1 = cv2.imread(fname_1)
        image_hsv_1 = cv2.cvtColor(image_1, cv2.COLOR_BGR2HSV)
        mean_ch_1, hist_hsv_1 = img_histo_hsv(image_hsv_1, mask_radius, i_min, i_max, plot)
        mean_ch_2, hist_hsv_2= img_histo_hsv(image_hsv_2, mask_radius, i_min, i_max, plot)
        gamma = [1, 1, 1]
        ch_range = [1, 2]
        for c in ch_range:
            f = lambda x: lumi_expect(hist_hsv_2[c], x, i_min, i_max) - mean_ch_1[c]
            gamma[c] = bisect(f, 0.1, 5)
        image_hsv_2 = adjust_gamma_ch3(image_hsv_2, gamma, ch_range)
        mean_ch_2, hist_hsv_2 = img_histo_hsv(image_hsv_2, mask_radius, i_min, i_max, plot)
        for c in ch_range:
            if verbose: print("{:.4f}->{:.4f} ({:+.2%}), gamma = {:.4f} ".format(mean_ch_1[c], mean_ch_2[c], 1-mean_ch_1[c]/mean_ch_2[c], gamma[c]))
    else:
        if verbose: print("saving file duplicate")
    image_2 = cv2.cvtColor(image_hsv_2, cv2.COLOR_HSV2BGR)
    cv2.imwrite(output_path+"/"+filename_2, image_2, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    
BALANCE_LUMI = "lumi"
BALANCE_RGB = "rgb"
BALANCE_SV = "sv"
BALANCE_LS = "ls"

def lumi_balance(input_path, output_path, mode=BALANCE_LUMI, ref_index=-1, mask_radius=-1, i_min=0, i_max=255, plot=False):
    fnames = file_folder(input_path)
    if ref_index==-1: ref = fnames[len(fnames)//2]
    fxnames = fnames
    for f in fxnames:
        if mode == BALANCE_LUMI:
            img_lumi_balance(ref, f, input_path, output_path, mask_radius, i_min, i_max, plot)
        elif mode == BALANCE_RGB:
            img_lumi_balance_rgb(ref, f, input_path, output_path, mask_radius, i_min, i_max, plot)
        elif mode == BALANCE_SV:
            img_lumi_balance_hsv(ref, f, input_path, output_path, mask_radius, i_min, i_max, plot)