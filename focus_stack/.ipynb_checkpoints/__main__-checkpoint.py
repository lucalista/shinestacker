EXTENSIONS = set(["bmp", "jpeg", "jpg", "png", "tif", "tiff"])

import os
import errno
import cv2
import argparse

import focus_stack as stk

def main(src_dir, dest_dir, choice, energy, pyramid_min_size, kernel_size, blur_size, smooth_size):
    src_contents = os.walk(src_dir)
    dirpath, _, fnames = next(src_contents)

    image_dir = os.path.split(dirpath)[-1]
    output_name = "{}_{}_{}".format(image_dir,choice,energy)
    if choice == stk.CHOICE_PYRAMID:
        output_name += "_m{}_k{}".format(pyramid_min_size, kernel_size)
    else:
        output_name += "_k{}_b{}_s{}".format(kernel_size,blur_size,smooth_size)
    output_name += ".png"
    output_file = os.path.join(dest_dir, output_name)

    try:
        os.makedirs(dest_dir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    print("Processing '" + image_dir + "' folder...")

    image_files = sorted([os.path.join(dirpath, name) for name in fnames])
    images = [cv2.imread(name) for name in image_files
              if os.path.splitext(name)[-1][1:].lower() in EXTENSIONS]

    if any([image is None for image in images]):
        raise RuntimeError("One or more input files failed to load.")

    stacked_image = stk.stack_focus(
        images = images,
        choice = choice,
        energy = energy,
        pyramid_min_size = pyramid_min_size,
        kernel_size = kernel_size,
        blur_size = blur_size,
        smooth_size = smooth_size
    )
    if (cv2.imwrite(output_file, stacked_image)):
        print("image saved to {}".format(output_file))
    else:
        print("an error occured")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Run the focus stacking algorithm on a set of images.')

    parser.add_argument('src_dir', metavar='SRC_DIR', type=str, help='the location of the source images')
    parser.add_argument('-d', '--dest-dir', metavar='DEST_DIR', type=str, default="images/output", help='the directory in which to place the stacked image')
    parser.add_argument('-c', '--choice', type=str, choices=[stk.CHOICE_PYRAMID, stk.CHOICE_AVERAGE, stk.CHOICE_MAX],
        default=stk.CHOICE_PYRAMID, dest='choice', help='the best-pixel selection strategy')
    parser.add_argument('-e', '--energy', type=str, choices=[stk.ENERGY_LAPLACIAN, stk.ENERGY_SOBEL],
        default=stk.ENERGY_LAPLACIAN, dest='energy', help='the energy function')
    parser.add_argument('-m', '--pyramid-min-size', type=int, default=32, dest='pyramid_min_size', help='the size of the smallest pyramid layer')
    parser.add_argument('-k', '--kernel', type=int, default=5, dest='kernel_size', help='the size of the kernel used in laplacian energy calculations')
    parser.add_argument('-b', '--blur', type=int, default=5, dest='blur_size', help='the size of the gaussian blur in laplacian energy calculation')    
    parser.add_argument('-s', '--smooth', type=int, default=32, dest='smooth_size', help='the size of the kernel use in bilaterally filtering the energy matrix. Not used for pyramid.')

    args = parser.parse_args()
    if args.choice == stk.CHOICE_PYRAMID and args.energy != stk.ENERGY_LAPLACIAN:
        raise RuntimeError("The pyramid best-pixel selection strategy can only be used with laplacian energy")
    if args.choice == stk.CHOICE_PYRAMID and args.kernel_size != 5:
        raise RuntimeError("The pyramid best-pixel selection strategy can only be used with a kernel size of 5")

    main(
        args.src_dir,
        args.dest_dir,
        args.choice,
        args.energy,
        args.pyramid_min_size,
        args.kernel_size,
        args.blur_size,
        args.smooth_size
    )
