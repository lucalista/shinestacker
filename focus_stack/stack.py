import numpy as np
import cv2
from .pyramid import get_pyramid_fusion
from .helper import image_set
from .helper import chunks
from .helper import file_folder
from .helper import check_file_exists
from .helper import copy_exif

def convert_to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def blend(images, focus_map):
    return np.sum(images.astype(np.float64) * focus_map[:, :, :, np.newaxis], axis=0).astype(images.dtype)

def get_sobel_map(images):
    energies = np.zeros(images.shape, dtype=np.float32)
    for index in range(images.shape[0]):
        image = images[index]
        energies[index] = np.abs(cv2.Sobel(image, cv2.CV_64F, 1, 0)) + np.abs(cv2.Sobel(image, cv2.CV_64F, 0, 1))
    return energies

def get_laplacian_map(images, kernel_size, blur_size):
    laplacian = np.zeros(images.shape, dtype=np.float32)
    for index in range(images.shape[0]):
        gaussian = cv2.GaussianBlur(images[index], (blur_size, blur_size), 0)
        laplacian[index] = np.abs(cv2.Laplacian(gaussian, cv2.CV_64F, ksize = kernel_size))
    return laplacian

def smooth_energy_map(energies, smooth_size):
    smoothed = np.zeros(energies.shape, dtype=energies.dtype)
    if (smooth_size > 0):
        for index in range(energies.shape[0]):
            smoothed[index] = cv2.bilateralFilter(energies[index], smooth_size, 25, 25)
    return smoothed

def get_focus_map(energies, choice):
    if (choice == CHOICE_AVERAGE):
        tile_shape = np.array(energies.shape)
        tile_shape[1:] = 1

        sum_energies = np.tile(np.sum(energies, axis=0), tile_shape)
        return np.divide(energies, sum_energies, where=sum_energies!=0)
    focus_map = np.zeros(energies.shape, dtype=np.float64)
    best_layer = np.argmax(energies, axis=0)
    for index in range(energies.shape[0]):
        focus_map[index] = best_layer == index
    return focus_map

ENERGY_SOBEL = "sobel"
ENERGY_LAPLACIAN = "laplacian"
CHOICE_PYRAMID = "pyramid"
CHOICE_MAX = "max"
CHOICE_AVERAGE = "average"

def stack_focus(images, choice = CHOICE_PYRAMID, energy = ENERGY_LAPLACIAN, pyramid_min_size = 32, kernel_size = 5, blur_size = 5, smooth_size = 32):
    images = np.array(images, dtype=images[0].dtype)
    if choice == CHOICE_PYRAMID:
        stacked_image = get_pyramid_fusion(images, pyramid_min_size, kernel_size)
        print('stack done')
        return cv2.convertScaleAbs(stacked_image)
    else:
        gray_images =np.zeros(images.shape[:-1], dtype=np.uint8)
        for index in range(images.shape[0]):
            gray_images[index] = convert_to_grayscale(images[index])
        if energy == ENERGY_SOBEL:
            energy_map = get_sobel_map(gray_images)
        else:
            energy_map = get_laplacian_map(gray_images, kernel_size, blur_size)
        if smooth_size > 0:
            energy_map = smooth_energy_map(energy_map, smooth_size)
    print('- get focus map')
    focus_map = get_focus_map(energy_map, choice)
    print('- blend images')
    stacked_image = blend(images, focus_map)
    print('- stack done')
    return cv2.convertScaleAbs(stacked_image)

def focus_stack(fnames, input_dir, output_dir, exif_dir='', postfix='', choice=CHOICE_PYRAMID, energy=ENERGY_LAPLACIAN):
    print('focus stack merge '+input_dir+', {} files: '.format(len(fnames))+', '.join(fnames))
    imgs = image_set(input_dir, fnames)
    s = stack_focus(imgs, choice=choice, energy=energy)
    f = fnames[0].split(".")
    fn = output_dir+"/"+f[0]+postfix+'.'+'.'.join(f[1:])
    cv2.imwrite(fn, s, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    if exif_dir != '':
        print("- save exif data")
        ex_fname = exif_dir+'/'+file_folder(exif_dir, verbose=False)[0]
        check_file_exists(ex_fname)
        copy_exif(ex_fname, fn, fn)
    
def focus_stack_chunks(input_dir, bactch_dir, exif_dir='', n_chunks=10, overlap=0, postfix='', choice=CHOICE_PYRAMID, energy=ENERGY_LAPLACIAN):
    cnk = chunks(input_dir, n_chunks, overlap)
    for c in cnk:
        focus_stack(c, input_dir, bactch_dir, exif_dir, postfix, choice, energy)
        
def focus_stack_dir(input_dir, output_dir, exif_dir='', postfix='_stack_avg', choice=CHOICE_PYRAMID, energy=ENERGY_LAPLACIAN):
    fnames = file_folder(input_dir)
    focus_stack(fnames, input_dir, output_dir, exif_dir, postfix, choice, energy)