import numpy as np
import torch
from sdeconv.deconv import SRichardsonLucy
from skimage import exposure, filters
from PIL import (ImageSequence, 
                 Image, 
                 TiffTags, 
                 TiffImagePlugin)

import matplotlib.pyplot as plt
import warnings 
import logging
import os
from astropy.io import fits


def open_tif_to_numpy(image_dir, crop_factor = 1):

    """ Opens an 8-bit TIFF file and reads the pixel intensities to a numpy array. Extracts original metadata information.

    Parameters
    ----------
    images_dir : str, path to raw image tiff file
    crop_factor : [0,1], determines crop in XY plane
    X : numpy array (z,x,y), holding pixel intensities
    metadata : original metadata of the raw image

    """
    
    # Read TIFF image stack properties from metadata
    with Image.open(image_dir, formats=['TIFF']) as img:

        meta_dict = {TiffTags.TAGS[key] : img.tag[key] for key in img.tag}
        numberFrames = meta_dict["n_frames"] = getattr(img, "n_frames", 1)
        imagePx = meta_dict["ImageWidth"][0]

        if img.tag_v2:  
            metadata = img.tag_v2 
        else:
            metadata = {}
        
        # Open TIFF image into a numpy array with crop factor. 
        cropped_Px = int(imagePx*crop_factor)
        X = np.zeros((numberFrames, cropped_Px, cropped_Px))
        left = top = int((imagePx-cropped_Px)/2)
        right =  bottom = cropped_Px + int((imagePx-cropped_Px)/2)

        for c, frame in enumerate(ImageSequence.Iterator(img)):
            
            frame = frame.crop((left, top, right, bottom))
            X[c,...] = frame

    return X, metadata


def extract_metadata(metadata):

    image_width_pixels = metadata[256]
    pixel_width_xy = 1/float(metadata[282])
    units =  metadata[270].split('unit=')[1].split('\n')[0]

    if "\nslices" in metadata[270]:
        numberFrames = int(metadata[270].split('slices=')[1].split('\n')[0])
        pixel_width_z = float(metadata[270].split('spacing=')[1].split('\n')[0])
    else:
        pixel_width_z, numberFrames = 1, 1

    return image_width_pixels, numberFrames, pixel_width_xy, pixel_width_z, units 


def normalize_numpy_8bit(array):

    """ Normalizes the image pixel intensity range from [min,max] to [0,255]

    Parameters
    ----------
    array : numpy array (two or three-dimensional)

    array_normalized : numpy array (two or three-dimensional)

    """

    array = np.nan_to_num(array, nan=0, posinf=255, neginf=0)
    
    min_val = np.min(array)
    max_val = np.max(array)
    
    if max_val == min_val:
        return np.zeros_like(array, dtype="uint8")  
    
    array_normalized = (array - np.min(array))* 255 / (np.max(array) - np.min(array))

    return array_normalized


def gaussian_kernel_smoothing(x,y,sigma):

        smoothed_values = np.zeros(y.shape)

        for x_position in x:

            kernel = np.exp(-((x - x_position) ** 2) / (2 * sigma**2))
            kernel = kernel / sum(kernel)
            smoothed_values[x_position] = sum(y * kernel)
            
        return smoothed_values


def preprocess_image(numpy_array, sigma = (2.5,2.5,2.5), truncate=0.2):

    """ Apply gaussian blurring and median filter to smoothen and denoise the image.

    Parameters
    ----------
    numpy_array : numpy array (two or three-dimensional)
    sigma : tuple of floats, standard deviation in pixels for the Gaussian kernel for z,x,y axes 
    truncate : float, truncates the filter after x standard deviations.

    numpy_array_gaus_med : numpy array (two or three-dimensional)

    """
   
    numpy_array_gaus = filters.gaussian(numpy_array, sigma = sigma, truncate=truncate) 
    
    numpy_array_gaus_med = filters.median(numpy_array_gaus)

    numpy_array_gaus_med = normalize_numpy_8bit(numpy_array_gaus_med)
    
    return numpy_array_gaus_med


def z_intensity_correction(stack, percentile = 0.999, min_val = 0, plot = False):

    """ Correction for the intensity attenuation across depth in 3D image stacks.

    Parameters
    ----------
    stack : numpy array (two or three-dimensional)
    percentile : float in [0,1], the selected n-th percentile pixel intensity value is used for the intensity correction at the specific image depth.
    min_value : float in [0,255], sets a constant lower intensity bound for the intensity correction at the specific image depth.
    plot : option for plotting the pixel intensities across z, before and after the correction

    stack_corrected : numpy array (two or three-dimensional)
    """

    def gaussian_kernel_smoothing(x,y,sigma):

        smoothed_values = np.zeros(y.shape)

        for x_position in x:

            kernel = np.exp(-((x - x_position) ** 2) / (2 * sigma**2))
            kernel = kernel / sum(kernel)
            smoothed_values[x_position] = sum(y * kernel)
            
        return smoothed_values

    def normalize_numpy_8bit_z(array, max_val, min_val = 0):

        """ Normalizes the image pixel intensity range from [0,255] to [0,max_val]

        Parameters
        ----------
        array : numpy array (two or three-dimensional)

        array_normalized : numpy array (two or three-dimensional)

        """

        if max_val == min_val:
            return np.zeros_like(array, dtype="uint8")  
    
        if min_val == 0:
            array_normalized = 255 * (array - np.min(array))/(max_val - np.min(array))
        
            array_normalized[array_normalized > 255] = 255
        else:
            array_normalized = 255 * (array - min_val)/(max_val - min_val)
        
            array_normalized[array_normalized > 255] = 255
            array_normalized[array_normalized < 0 ] = 0

        return array_normalized


    '''
    Correction of z-attenuation in the stack based on a set percentile intensity value. Ideally, the percentile is set to the largest possible value in [0,1], so we get a smooth curve to capture the attenuation in intensity with z-slices.
    A percentile of 1 sets the maximum to the maximum pixel intensity in the z-slice, but usually gives a noisy measure.  
    '''

    stack_corrected = np.copy(stack)
    intensity_z, intensity_z_min, intensity_z_max, intensity_z_after  = [], [], [], []
    percentile = percentile

    for i in np.arange(0,stack.shape[0]):

        maxi = np.max(stack[i,...])  # Maximum pixel intensity in the slice
        minimum = np.min(stack[i,...])  # Average pixel intensity in the slice
        percentage = np.quantile(stack[i,...], percentile) # nth- percentile pixel intensity in the slice

        intensity_z.append(percentage)
        intensity_z_min.append(minimum)
        intensity_z_max.append(maxi)
        
    intensity_z_smoothed = gaussian_kernel_smoothing(np.arange(stack.shape[0]), np.array(intensity_z), sigma = 10)
    intensity_z_min_smoothed = gaussian_kernel_smoothing(np.arange(stack.shape[0]), np.array(intensity_z_min), sigma = 10)
    intensity_z_max_smoothed = gaussian_kernel_smoothing(np.arange(stack.shape[0]), np.array(intensity_z_max), sigma = 10)

    for i in np.arange(0,stack.shape[0]):

        stack_corrected[i,...] = normalize_numpy_8bit_z(stack_corrected[i,...], intensity_z_smoothed[i], min_val)   # Re-normalized pixel intensities in the slice
        corrected_perc = np.quantile(stack_corrected[i,...], percentile) # Nth- percentile pixel intensity in the corrected slice
        intensity_z_after.append(corrected_perc)
    
    intensity_z_after_smoothed = gaussian_kernel_smoothing(np.arange(stack.shape[0]), np.array(intensity_z_after), sigma = 10)

    if plot == True:
        x = np.arange(0,stack.shape[0])

        plt.figure(figsize=(5,3), dpi=300)
        plt.plot(x, intensity_z_max, 'o', ms = 2, color = "mediumvioletred")
        plt.plot(x, intensity_z_max_smoothed, linewidth = 3, color = "mediumvioletred", label="no z-correction (max)") 
        plt.plot(x, intensity_z, 'o', ms = 2, color = "deeppink")
        plt.plot(x, intensity_z_smoothed, linewidth = 3, color = "deeppink", label=f"no z-correction ($P_{{{percentile*100}}}$)") 
        plt.plot(x, intensity_z_min_smoothed, linewidth = 3, color = "lightpink", label="no z-correction (min)") 
        plt.plot(x, intensity_z_after, 'co', ms = 2) 
        plt.plot(x, intensity_z_after_smoothed, linewidth = 3, color = "c", label=f"z-correction ($P_{{{percentile*100}}}$)")

        plt.legend(fontsize= 10, loc = "lower right", frameon = False)
        plt.xlabel("Z-slice")
        plt.ylabel("Intensity")
        plt.tight_layout()
        plt.minorticks_on()
        plt.tick_params(direction='in', which= "both", top = True, right = True)
        plt.show()

    return stack_corrected


def RL_deconvolution(img_stack, psf, iter):
    
    """ Richardson-Lucy deconvolution from sdeconv Python framework

    Parameters
    ----------
    img_stack : numpy array (two or three-dimensional)
    psf: numpy array
    iter: int, number of iterations to carry out

    deconv : numpy array (two or three-dimensional)
    """
    
    img_d = torch.from_numpy(img_stack)
    filter_ = SRichardsonLucy(psf, niter=iter, pad=10)
    out_image = filter_(img_d)
    deconv = out_image.numpy()
    deconv = normalize_numpy_8bit(deconv)

    return deconv


def save_numpy_to_8bit_tif(images_to_tif, filename, metadata):

    """ Writes the processed numpy image data to an 8-bit TIFF file with original metadata information.

    Parameters
    ----------
    images_to_tif : numpy array (two or three-dimensional)
    filename : str, for the name of the tiff file
    metadata : original metadata of the raw image

    """
    
    imlist = []
    images_to_tif =  normalize_numpy_8bit(images_to_tif) 


    if len (images_to_tif.shape) == 3:
        for image_to_tif in images_to_tif:
            u8in = image_to_tif.astype("uint8")
            img_out = Image.fromarray(u8in)  

            ifd = TiffImagePlugin.ImageFileDirectory_v2()

            for key, value in metadata.items():
                tag = TiffTags.TAGS.get(key, None)

                if tag is not None:
                    ifd[key] = value
                        
            imlist.append(img_out)

        imlist[0].save(filename, compression="tiff_deflate", save_all=True,
                    append_images=imlist[1:], tiffinfo = ifd)
    
    if len (images_to_tif.shape) == 2:
        u8in = images_to_tif.astype("uint8")
        img_out = Image.fromarray(u8in)

        ifd = TiffImagePlugin.ImageFileDirectory_v2()

        for key, value in metadata.items():
            tag = TiffTags.TAGS.get(key, None)

            if tag is not None:
                ifd[key] = value

        imlist.append(img_out)
        imlist[0].save(filename, compression="tiff_deflate", save_all=True,
                            append_images=imlist[1:], tiffinfo = ifd)


def save_fits(image, filename, path=None):

    """ Convert and save an np.array image into fits file to run Disperse.
    Function from Merle et. al. (2023), doi: 10.1016/J.DEVCEL.2023.07.017

    Parameters
    ----------
    image : numpy array
    filename: string, name of fits file
    path: string
    """

    hdu = fits.PrimaryHDU(image)
    if filename[-5:] != '.fits':
        filename = filename + '.fits'
    if path is None:
        warnings.warn("Fits file will be saved in the working directory. \
                       Or maybe path is specify in filename...")
        path = os.getcwd()

    hdu.writeto(os.path.join(path, filename), overwrite=True)

    logging.info('Saved file: {filename} into {path} directory')



    
