import logging
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import torch
from astropy.io import fits
from PIL import Image, ImageSequence, TiffImagePlugin, TiffTags
from sdeconv.deconv import SRichardsonLucy
from skimage import filters


def open_tif_to_numpy(image_dir, crop_factor=1):
    """
    Read an 8-bit TIFF (stack) into a (z, x, y) array, cropped in XY. Returns the original metadata.
    """
    with Image.open(image_dir, formats=['TIFF']) as img:
        n_frames = getattr(img, "n_frames", 1)
        image_px = img.tag[256][0]  # ImageWidth
        metadata = img.tag_v2 if img.tag_v2 else {}

        cropped_px = int(image_px * crop_factor)
        X = np.zeros((n_frames, cropped_px, cropped_px))
        left = top = int((image_px - cropped_px) / 2)
        right = bottom = cropped_px + int((image_px - cropped_px) / 2)

        for c, frame in enumerate(ImageSequence.Iterator(img)):
            X[c, ...] = frame.crop((left, top, right, bottom))

    return X, metadata


def extract_metadata(metadata):
    image_width_pixels = metadata[256]
    pixel_width_xy = 1 / float(metadata[282])
    units = metadata[270].split('unit=')[1].split('\n')[0]

    if "\nslices" in metadata[270]:
        number_frames = int(metadata[270].split('slices=')[1].split('\n')[0])
        pixel_width_z = float(metadata[270].split('spacing=')[1].split('\n')[0])
    else:
        pixel_width_z, number_frames = 1, 1

    return image_width_pixels, number_frames, pixel_width_xy, pixel_width_z, units


def normalize_numpy_8bit(array):
    """
    Rescale intensities from [min, max] to [0, 255]
    """
    array = np.nan_to_num(array, nan=0, posinf=255, neginf=0)
    min_val = np.min(array)
    max_val = np.max(array)

    if max_val == min_val:
        return np.zeros_like(array, dtype="uint8")

    return (array - min_val) * 255 / (max_val - min_val)


def gaussian_kernel_smoothing(x, y, sigma):
    smoothed_values = np.zeros(y.shape)

    for x_position in x:
        kernel = np.exp(-((x - x_position) ** 2) / (2 * sigma**2))
        kernel = kernel / sum(kernel)
        smoothed_values[x_position] = sum(y * kernel)

    return smoothed_values


def preprocess_image(numpy_array, sigma=(2.5, 2.5, 2.5), truncate=0.2):
    """
    Gaussian blur and median filter, then normalize to [0, 255].
    """
    smoothed = filters.gaussian(numpy_array, sigma=sigma, truncate=truncate)
    smoothed = filters.median(smoothed)
    return normalize_numpy_8bit(smoothed)


def normalize_numpy_8bit_z(array, max_val, min_val=0):
    """
    Rescale a z-slice to [0, 255], with max_val as the upper bound (min_val=0 uses the slice minimum).
    """
    if max_val == min_val:
        return np.zeros_like(array, dtype="uint8")

    if min_val == 0:
        array_normalized = 255 * (array - np.min(array)) / (max_val - np.min(array))
    else:
        array_normalized = 255 * (array - min_val) / (max_val - min_val)

    array_normalized[array_normalized > 255] = 255
    if min_val != 0:
        array_normalized[array_normalized < 0] = 0

    return array_normalized


def z_intensity_correction(stack, percentile=0.999, min_val=0, plot=False):
    """
    Correct intensity attenuation with depth, using a smoothed n-th percentile intensity per z-slice
    (a percentile close to 1 gives a smooth curve; 1 itself is noisy).
    """
    z = np.arange(stack.shape[0])
    stack_corrected = np.copy(stack)

    intensity_z = [np.quantile(stack[i, ...], percentile) for i in z]
    intensity_z_smoothed = gaussian_kernel_smoothing(z, np.array(intensity_z), sigma=10)

    for i in z:
        stack_corrected[i, ...] = normalize_numpy_8bit_z(stack_corrected[i, ...], intensity_z_smoothed[i], min_val)

    if plot:
        intensity_z_min = [np.min(stack[i, ...]) for i in z]
        intensity_z_max = [np.max(stack[i, ...]) for i in z]
        intensity_z_after = [np.quantile(stack_corrected[i, ...], percentile) for i in z]

        intensity_z_min_smoothed = gaussian_kernel_smoothing(z, np.array(intensity_z_min), sigma=10)
        intensity_z_max_smoothed = gaussian_kernel_smoothing(z, np.array(intensity_z_max), sigma=10)
        intensity_z_after_smoothed = gaussian_kernel_smoothing(z, np.array(intensity_z_after), sigma=10)

        plt.figure(figsize=(5, 3), dpi=300)
        plt.plot(z, intensity_z_max, 'o', ms=2, color="mediumvioletred")
        plt.plot(z, intensity_z_max_smoothed, linewidth=3, color="mediumvioletred", label="no z-correction (max)")
        plt.plot(z, intensity_z, 'o', ms=2, color="deeppink")
        plt.plot(z, intensity_z_smoothed, linewidth=3, color="deeppink", label=f"no z-correction ($P_{{{percentile*100}}}$)")
        plt.plot(z, intensity_z_min_smoothed, linewidth=3, color="lightpink", label="no z-correction (min)")
        plt.plot(z, intensity_z_after, 'co', ms=2)
        plt.plot(z, intensity_z_after_smoothed, linewidth=3, color="c", label=f"z-correction ($P_{{{percentile*100}}}$)")

        plt.legend(fontsize=10, loc="lower right", frameon=False)
        plt.xlabel("Z-slice")
        plt.ylabel("Intensity")
        plt.tight_layout()
        plt.minorticks_on()
        plt.tick_params(direction='in', which="both", top=True, right=True)
        plt.show()

    return stack_corrected


def RL_deconvolution(img_stack, psf, n_iter):
    """
    Richardson-Lucy deconvolution (sdeconv), output normalized to [0, 255].
    """
    filter_ = SRichardsonLucy(psf, niter=n_iter, pad=10)
    deconv = filter_(torch.from_numpy(img_stack)).numpy()
    return normalize_numpy_8bit(deconv)


def save_numpy_to_8bit_tif(images_to_tif, filename, metadata):
    """
    Write a 2D image or 3D stack to an 8-bit TIFF, keeping the original metadata tags.
    """
    images_to_tif = normalize_numpy_8bit(images_to_tif)

    if images_to_tif.ndim == 2:
        images_to_tif = images_to_tif[np.newaxis]
    if images_to_tif.ndim != 3:
        return

    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    for key, value in metadata.items():
        if TiffTags.TAGS.get(key, None) is not None:
            ifd[key] = value

    imlist = [Image.fromarray(image.astype("uint8")) for image in images_to_tif]
    imlist[0].save(filename, compression="tiff_deflate", save_all=True,
                   append_images=imlist[1:], tiffinfo=ifd)


def save_fits(image, filename, path=None):
    """
    Save a numpy image as a .fits file to run DisPerSE.
    From Merle et al. (2023), doi: 10.1016/J.DEVCEL.2023.07.017
    """
    hdu = fits.PrimaryHDU(image)
    if not filename.endswith('.fits'):
        filename = filename + '.fits'
    if path is None:
        warnings.warn("Fits file will be saved in the working directory.")
        path = os.getcwd()

    hdu.writeto(os.path.join(path, filename), overwrite=True)

    logging.info(f'Saved file: {filename} into {path} directory')