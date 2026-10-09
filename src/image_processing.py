import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

from miplib.data.containers.fourier_correlation_data import FourierCorrelationDataCollection
from miplib.data.containers.image import Image
from miplib.ui.cli import miplib_entry_point_options as options
from miplib.analysis.resolution import fourier_ring_correlation as frc

from sdeconv.psfs import SPSFGaussian

from denoise_contrast_enhance import (open_tif_to_numpy,
                                      gaussian_kernel_smoothing,
                                      RL_deconvolution,
                                      normalize_numpy_8bit,
                                      preprocess_image,
                                      z_intensity_correction,
                                      save_numpy_to_8bit_tif,
                                      save_fits)


def frc_resolution(image_object, args):
    try:
        frc_results = FourierCorrelationDataCollection()
        frc_results[0] = frc.calculate_single_image_frc(
            image_object, args, z_correction=image_object.spacing[0] / image_object.spacing[1])
        return frc_results[0].resolution['resolution']
    except Exception as e:
        print(f"FRC resolution calculation failed: {e}")
        return np.nan


def mean_frc_resolution_xy(img_stack, img_spacing, args):
    print("The image dimensions are {} and spacing {} um.".format(img_stack.shape, img_spacing))

    if img_stack.ndim == 2:
        mean_res_xy = frc_resolution(Image(img_stack, (img_spacing[1], img_spacing[2])), args)
    else:
        res_xy = []
        for i in range(img_stack.shape[0]):
            res_xy.append(frc_resolution(Image(img_stack[i, ...], (img_spacing[1], img_spacing[2])), args))
        mean_res_xy = np.nanmean(res_xy)

    print("Average XY resolution = ", mean_res_xy)
    return mean_res_xy


def mean_frc_resolution_yz(img_stack, img_spacing, args):
    res_yz = []
    for i in np.linspace(0, img_stack.shape[1] - 1, 50).astype(int):
        res_yz.append(frc_resolution(Image(img_stack[..., i], [img_spacing[0], img_spacing[1]]), args))

    mean_res_yz = np.nanmean(res_yz)
    print("Average YZ resolution = ", mean_res_yz)
    return mean_res_yz


def image_processing(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)

    base_path = Path(config["path"])
    path_to_dir = str(base_path / config["path_to_dir"].strip("/")) + "/"
    path_to_output = str(base_path / config["path_to_output"].strip("/")) + "/"

    image = config["image"]
    pixel_spacing = config["pixel_spacing"]
    std = config["std"]
    truncate = config["truncate"]
    upper = config["upper"]
    lower = config["lower"]
    n_iter = config["iter"]

    print("input: ", path_to_dir, ", output: ", path_to_output)

    raw_stack, metadata = open_tif_to_numpy(path_to_dir + image, crop_factor=1)
    is_2d = raw_stack.shape[0] == 1

    # denoise + intensity correction
    if is_2d:
        raw_stack = raw_stack[0, ...]
        processed = preprocess_image(raw_stack, sigma=(std, std), truncate=truncate)
    else:
        processed = z_intensity_correction(
            preprocess_image(raw_stack, sigma=(std, std, std), truncate=truncate),
            percentile=upper, min_val=lower, plot=False)

    # FRC resolution estimate -> Gaussian PSF
    args = options.get_deconvolve_script_options(
        "image psf --max-nof-iterations=10 --first-estimate=image --blocks=1 --pad=100 "
        "--resolution-threshold-criterion=fixed --tv-lambda=0 --frc-curve-fit-type=polynomial "
        "--frc-curve-fit-degree=10 --update-blind-psf=-50 --bin-delta=3".split())

    resolution_xy = mean_frc_resolution_xy(processed, pixel_spacing, args)
    psf = None

    if is_2d:
        print("Resolution estimate (um): ", resolution_xy)
        if not math.isnan(resolution_xy):
            pixel_res_xy = math.floor(resolution_xy / pixel_spacing[1])
            psf_generator = SPSFGaussian(sigma=(pixel_res_xy, pixel_res_xy), shape=(raw_stack.shape))
            psf = psf_generator()
    else:
        resolution_yz = mean_frc_resolution_yz(processed, pixel_spacing, args)
        print("Resolution estimate (um): ", resolution_xy, resolution_yz)
        if not math.isnan(resolution_xy) and not math.isnan(resolution_yz):
            pixel_res_xy = math.floor(resolution_xy / pixel_spacing[1])
            pixel_res_z = math.floor(resolution_yz / pixel_spacing[0])
            psf_generator = SPSFGaussian(sigma=(pixel_res_z, pixel_res_xy, pixel_res_xy), shape=(raw_stack.shape))
            psf = psf_generator()

    # deconvolution
    if psf is not None:
        deconv_res = RL_deconvolution(processed, psf, n_iter)
        deconvolved = z_intensity_correction(deconv_res, percentile=0.99990, min_val=0, plot=False)
    else:
        print("Skipping deconvolution.")
        deconvolved = processed

    save_numpy_to_8bit_tif(deconvolved, filename=path_to_output + f"processed_{image}", metadata=metadata)
    save_fits(deconvolved, f"processed_{image}", path=path_to_output)

    # overview figure
    img_1 = normalize_numpy_8bit(raw_stack)
    img_2 = normalize_numpy_8bit(processed)
    img_3 = normalize_numpy_8bit(deconvolved)
    if len(deconvolved.shape) == 3:
        img_1, img_2, img_3 = np.max(img_1, axis=0), np.max(img_2, axis=0), np.max(img_3, axis=0)

    plt.figure(figsize=(6, 4), dpi=600)
    plt.subplot(2, 3, 1)
    plt.imshow(img_1, cmap='magma', vmin=0, vmax=255)
    plt.axis('off')
    plt.title("1- original", fontsize=8)
    plt.tight_layout(pad=0.1)
    plt.subplot(2, 3, 2)
    plt.imshow(img_2, cmap='magma', vmin=0, vmax=255)
    plt.axis('off')
    plt.title("2- denoised + intensity corrected", fontsize=8)
    plt.tight_layout(pad=0.1)
    plt.subplot(2, 3, 3)
    plt.imshow(img_3, cmap='magma', vmin=0, vmax=255)
    plt.axis('off')
    plt.title("3- deconvoluted", fontsize=8)
    plt.tight_layout(pad=0.1)

    if len(deconvolved.shape) == 3:
        x = np.arange(0, raw_stack.shape[0])
        intensity_z, intensity_z_after = [], []
        for i in x:
            intensity_z.append(np.quantile(raw_stack[i, ...], upper))
            intensity_z_after.append(np.quantile(processed[i, ...], upper))

        intensity_z_smoothed = gaussian_kernel_smoothing(x, np.array(intensity_z), sigma=10)
        intensity_z_after_smoothed = gaussian_kernel_smoothing(x, np.array(intensity_z_after), sigma=10)

        plt.subplot(2, 3, 5)
        plt.plot(x, intensity_z, 'o', ms=1, color="m")
        plt.plot(x, intensity_z_smoothed, linewidth=2, color="m", label=f"no z-correction ($P_{{{upper*100}}}$)")
        plt.plot(x, intensity_z_after, 'ko', ms=1)
        plt.plot(x, intensity_z_after_smoothed, linewidth=2, color="k", label=f"z-correction ($P_{{{upper*100}}}$)")
        plt.legend(fontsize=6, loc="lower right", frameon=False)
        plt.xlabel("z-slice", fontsize=8)
        plt.ylabel("intensity", fontsize=8)
        plt.ylim(0, 260)
        plt.minorticks_on()
        plt.tick_params(direction='in', which="both", top=True, right=True)

    plt.tight_layout(pad=0.1)
    Path(path_to_output, "figures").mkdir(parents=True, exist_ok=True)
    plt.savefig(path_to_output + f"figures/overview_{image}.png", dpi=600, pad_inches=0, bbox_inches='tight')
    plt.show()

    return raw_stack, deconvolved


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    image_processing(parser.parse_args().config)