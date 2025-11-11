import yaml
from pathlib import Path
import numpy as np
import networkx as nx
import math
import matplotlib.pyplot as plt
import sys

import miplib
from miplib.data.containers.fourier_correlation_data import FourierCorrelationDataCollection
from miplib.data.containers.image import Image
from miplib.ui.cli import miplib_entry_point_options as options
from miplib.analysis.resolution import fourier_ring_correlation as frc
from miplib.ui.plots import frc as frcplots


sys.path.insert(1, '/Users/Work/Desktop/Master/ARP/fiber_feature_analysis/')
sys.path.insert(1, '/Users/Work/Desktop/Master/ARP/fiber_feature_analysis/src/')

# SDeconv python framework for PSF generation and deconvolution of 3D images
from sdeconv.psfs import SPSFGaussian, SPSFGibsonLanni
from sdeconv.deconv import SRichardsonLucy

# Image processing functions 
from denoise_contrast_enhance import (open_tif_to_numpy,
                                      gaussian_kernel_smoothing,
                                      RL_deconvolution, 
                                      normalize_numpy_8bit, 
                                      preprocess_image,
                                      z_intensity_correction, 
                                      save_numpy_to_8bit_tif,
                                      save_fits)



def image_processing(config_path):

    def argument_list_FRC(fit_type, fit_degree, bin_number):

        n_iterations = 10
        args_list = ("image psf"  
                " --max-nof-iterations={}  --first-estimate=image" 
                " --blocks=1 --pad=100 --resolution-threshold-criterion=fixed"
                f" --tv-lambda=0  --frc-curve-fit-type={fit_type} --frc-curve-fit-degree={fit_degree} --update-blind-psf=-50 --bin-delta={bin_number}").format(n_iterations).split()
        
        args = options.get_deconvolve_script_options(args_list)

        return args


    def compute_single_FRC_resolution(image_object, args, plot = False):

        frc_results = FourierCorrelationDataCollection()
        frc_results[0] = frc.calculate_single_image_frc(image_object, args, z_correction = image_object.spacing[0]/image_object.spacing[1])

        if plot == True:
            plotter = frcplots.FourierDataPlotter(frc_results)
            plotter.plot_one(0)


        return frc_results[0].resolution['resolution'], frc_results


    def compute_average_FRC_resolution_XY(img_stack, img_spacing, args):

        print ("The image dimensions are {} and spacing {} um.".format(img_stack.shape, img_spacing))
        res_xy = []

        if img_stack.ndim == 2:
            image_2d_xy = Image(img_stack, (img_spacing[1], img_spacing[2]))
            frc_resolution, frc_object = compute_single_FRC_resolution(image_2d_xy, args, plot=False)
            mean_res_xy = frc_resolution
        else:
            for i in range (img_stack.shape[0]):
                image_2d_xy = Image(img_stack[i,...], (img_spacing[1], img_spacing[2]))
                frc_resolution, frc_object = compute_single_FRC_resolution(image_2d_xy, args, plot=False)
                res_xy.append(frc_resolution)

        mean_res_xy = np.mean(res_xy)

        # if plot == True:
        #     plot_frc_curve(frc_object, args)
        print ("Average XY resolution = ", mean_res_xy )

        return mean_res_xy

    def compute_average_FRC_resolution_YZ(img_stack, img_spacing, args):

        res_yz = []

        for i in np.linspace(0,img_stack.shape[1]-1, 50).astype(int):
            slice_yz = img_stack[...,i]
            frc_resolution, frc_object = compute_single_FRC_resolution(Image(slice_yz , [img_spacing[0], img_spacing[1]]), args, plot = False)
            res_yz.append(frc_resolution)
            
            
        mean_res_yz = np.mean(res_yz)
        print ("Average YZ resolution = ", mean_res_yz )

        return mean_res_yz
    

    with open(config_path) as f:
        config = yaml.safe_load(f)

    base_path = Path(config["path"])
    path_to_dir = str(base_path / config["path_to_dir"].strip("/"))  + "/"
    path_to_output = str(base_path / config["path_to_output"].strip("/"))  + "/"

    image = config["image"]
    pixel_spacing = config["pixel_spacing"]
    std = config["std"]
    truncate = config["truncate"]
    upper = config["upper"]
    lower = config["lower"]
    iter = config["iter"]

    print ("input: ", path_to_dir, ", output: ", path_to_output,)

    raw_stack , metadata = open_tif_to_numpy(path_to_dir + image, crop_factor= 1)

    is_2d = raw_stack.shape[0] == 1

    if is_2d: # 2D image 
        raw_stack = raw_stack[0, ...]
        processed_stack_intensity_correction = preprocess_image(raw_stack, sigma = (std,std), truncate = truncate)
    else:
        processed_stack_intensity_correction = z_intensity_correction(preprocess_image(raw_stack, sigma = (std,std,std), truncate = truncate), percentile = upper, min_val = lower, plot = False)

    ## FRC RESOLUTION ESTIMATE
    fit_type = "polynomial"
    fit_degree = "10"
    bin_number = "3"
    args = argument_list_FRC(fit_type, fit_degree, bin_number)

    resolution_XY = compute_average_FRC_resolution_XY(processed_stack_intensity_correction, pixel_spacing, args)
    
    if is_2d: # 2D image 
        print( "Resolution estimate (um): " , resolution_XY)

        if not math.isnan(resolution_XY):
            pixel_res_xy = math.floor(resolution_XY/pixel_spacing[1])  
            psf_generator = SPSFGaussian(sigma=(pixel_res_xy, pixel_res_xy), shape=(raw_stack.shape))
            psf = psf_generator()
            deconv_res = RL_deconvolution(processed_stack_intensity_correction, psf, iter)
            deconv_res_intensity_correction = z_intensity_correction(deconv_res , percentile = 0.99990, min_val = 0, plot = False)
        else:
            print("Skipping deconvolution.")
            deconv_res_intensity_correction = processed_stack_intensity_correction   

    else:  # 3D image
        resolution_YZ = compute_average_FRC_resolution_YZ(processed_stack_intensity_correction, pixel_spacing, args)
        print( "Resolution estimate (um): " , resolution_XY, resolution_YZ)

        if not math.isnan(resolution_XY) and not math.isnan(resolution_YZ):
            pixel_res_xy = math.floor(resolution_XY/pixel_spacing[1])  
            pixel_res_z = math.floor(resolution_YZ/pixel_spacing[0])  
            psf_generator = SPSFGaussian(sigma=(pixel_res_z, pixel_res_xy, pixel_res_xy), shape=(raw_stack.shape))
            psf = psf_generator()
            deconv_res = RL_deconvolution(processed_stack_intensity_correction, psf, iter)
            deconv_res_intensity_correction = z_intensity_correction(deconv_res , percentile = 0.99990, min_val = 0, plot = False)
        else:
            print("Skipping deconvolution.")
            deconv_res_intensity_correction = processed_stack_intensity_correction   


    # Gibson and Lanni PSF: experimental parameters related to the sample, objective lens, imersion medium and imaging settings are filled in.
    # psf_generator = SPSFGibsonLanni(raw_stack.shape, 
    #                                 NA=1.3, wavelength=0.488, M=63, ns=1.33, ng0=1.5, ng=1.5, ni0=1.47, ni=1.47, 
    #                                 ti0=150, tg0=170, tg=170, res_lateral= pixel_spacing[1], res_axial=pixel_spacing[0], pZ=0, use_square=True)


   

    # Save processed image and fits file
    save_numpy_to_8bit_tif(deconv_res_intensity_correction,  filename = path_to_output + f"processed_{image}", metadata=metadata)
    save_fits(deconv_res_intensity_correction, f"processed_{image}", path = path_to_output)

    cmp = 'magma'


    if len(deconv_res_intensity_correction.shape)==3:
            
        plt.figure(figsize=(6,4), dpi=600)
        plt.subplot(2,3,1)
        plt.imshow(np.max(normalize_numpy_8bit(raw_stack), axis=0), cmap=cmp, vmin=0, vmax=255)
        plt.axis('off')
        plt.title("1- original", fontsize = 8)
        plt.tight_layout(pad=0.1)
        plt.subplot(2,3,2)
        plt.imshow(np.max(normalize_numpy_8bit(processed_stack_intensity_correction), axis=0), cmap=cmp, vmin=0, vmax=255)
        plt.axis('off')
        plt.title("2- denoised + intensity corrected", fontsize = 8)
        plt.tight_layout(pad=0.1)
        plt.subplot(2,3,3)
        plt.imshow(np.max(normalize_numpy_8bit(deconv_res_intensity_correction), axis=0), cmap=cmp, vmin=0, vmax=255)
        plt.axis('off')
        plt.title("3- deconvoluted", fontsize = 8)
        plt.tight_layout(pad=0.1)

        intensity_z, intensity_z_min, intensity_z_max, intensity_z_after  = [], [], [], []
        x = np.arange(0,raw_stack.shape[0])

        for i in np.arange(0,raw_stack.shape[0]):
            maxi = np.max(raw_stack[i,...])  # Maximum pixel intensity in the slice
            minimum = np.min(raw_stack[i,...])  # Average pixel intensity in the slice
            percentage = np.quantile(raw_stack[i,...], upper) # nth- percentile pixel intensity in the slice
            intensity_z.append(percentage)
            intensity_z_min.append(minimum)
            intensity_z_max.append(maxi)
            corrected_perc = np.quantile(processed_stack_intensity_correction[i,...], upper) # Nth- percentile pixel intensity in the corrected slice
            intensity_z_after.append(corrected_perc)
        
        intensity_z_smoothed = gaussian_kernel_smoothing(np.arange(raw_stack.shape[0]), np.array(intensity_z), sigma = 10)
        intensity_z_after_smoothed = gaussian_kernel_smoothing(np.arange(processed_stack_intensity_correction.shape[0]), np.array(intensity_z_after), sigma = 10)
    
        plt.subplot(2,3,5)
        plt.plot(x, intensity_z, 'o', ms = 1, color = "m")
        plt.plot(x, intensity_z_smoothed, linewidth = 2, color = "m", label=f"no z-correction ($P_{{{upper*100}}}$)") 
        plt.plot(x, intensity_z_after, 'ko', ms = 1) 
        plt.plot(x, intensity_z_after_smoothed, linewidth = 2, color = "k", label=f"z-correction ($P_{{{upper*100}}}$)")
        plt.legend(fontsize= 6, loc = "lower right", frameon = False)
        plt.xlabel("z-slice", fontsize= 8)
        plt.ylabel("intensity", fontsize= 8)
        plt.ylim(0,260)
        plt.minorticks_on()
        plt.tick_params(direction='in', which= "both", top = True, right = True)

        plt.tight_layout(pad=0.1)
        plt.savefig(path_to_output + f"figures/overview_{image}.png", dpi=600, pad_inches=0, bbox_inches='tight')
        plt.show()

    else:
        
        plt.figure(figsize=(6,4), dpi=600)
        plt.subplot(2,3,1)
        plt.imshow(normalize_numpy_8bit(raw_stack), cmap=cmp, vmin=0, vmax=255)
        plt.axis('off')
        plt.title("1- original", fontsize = 8)
        plt.tight_layout(pad=0.1)
        plt.subplot(2,3,2)
        plt.imshow(normalize_numpy_8bit(processed_stack_intensity_correction), cmap=cmp, vmin=0, vmax=255)
        plt.axis('off')
        plt.title("2- denoised + intensity corrected", fontsize = 8)
        plt.tight_layout(pad=0.1)
        plt.subplot(2,3,3)
        plt.imshow(normalize_numpy_8bit(deconv_res_intensity_correction), cmap=cmp, vmin=0, vmax=255)
        plt.axis('off')
        plt.title("3- deconvoluted", fontsize = 8)
        plt.tight_layout(pad=0.1)

        
        plt.tight_layout(pad=0.1)
        plt.savefig(path_to_output + f"figures/overview_{image}.png", dpi=600, pad_inches=0, bbox_inches='tight')
        plt.show()


    return raw_stack, deconv_res_intensity_correction  #deconv_res_intensity_correction #normalize_numpy_8bit(raw_stack), processed_stack_intensity_correction

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    image_processing(args.config)
