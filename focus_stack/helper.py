import os
import cv2
from PIL import Image
import time

def print_elapsed_time(start):
    dt = time.time() - start
    mm = int(dt // 60)
    ss = dt - mm*60
    print("elapsed time: {}:{:.2f}s".format(mm, ss))

def mkdir(d):
    if not os.path.exists(d): os.makedirs(d)
    
def check_file_exists(filename):
    if(not os.path.isfile(filename)): raise Exception("File does not exist: " + filename)
    
EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

def file_folder(src_dir, verbose=True):
    src_contents = os.walk(src_dir)
    dirpath, _, fnames = next(src_contents)
    fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS]
    if verbose:
        print("Folder: '" + src_dir + "'")
        print('- {} files: '.format(len(fnames))+', '.join(fnames))
    return fnames

def image_set(src_dir, fnames):
    image_files = sorted([os.path.join(src_dir, name) for name in fnames])
    image_files = [cv2.imread(name) for name in image_files]
    if any([image is None for image in image_files]):
        raise RuntimeError("One or more input files failed to load.")
    return image_files

def chunks(path, n_files, overlap=0):
    if overlap >= n_files: raise Exception("Overlap must be smaller than batch size")
    fnames = file_folder(path)
    return [fnames[x:x + n_files] for x in range(0, len(fnames), n_files - overlap)]

def copy_exif(input_exif, input_img, output_img):
    image = Image.open(input_exif)
    exif = image.info['exif']
    image_new = Image.open(input_img)
    image_new.save(output_img, 'JPEG', exif=exif)