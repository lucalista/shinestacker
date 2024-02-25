import os
import cv2

def mkdir(d):
    if not os.path.exists(d): os.makedirs(d)
    
def check_file_exists(filename):
    if(not os.path.isfile(filename)): raise Exception("File does not exist: " + filename)
    
EXTENSIONS = set(["jpeg", "jpg", "png", "tif", "tiff"])

def file_folder(src_dir):
    src_contents = os.walk(src_dir)
    dirpath, _, fnames = next(src_contents)
    fnames = [name for name in fnames if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS]
    print("Folder: '" + src_dir + "'")
    print('- {} files: '.format(len(fnames))+', '.join(fnames))
    return fnames

def image_set(src_dir, fnames):
    image_files = sorted([os.path.join(src_dir, name) for name in fnames])
    image_files = [cv2.imread(name) for name in image_files]
    if any([image is None for image in image_files]):
        raise RuntimeError("One or more input files failed to load.")
    return image_files

def chunks(path, l):
    fnames = file_folder(path)
    return [fnames[x:x+l] for x in range(0, len(fnames), l)]