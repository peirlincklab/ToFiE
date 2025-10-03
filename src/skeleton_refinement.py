import yaml
from pathlib import Path
from denoise_contrast_enhance import open_tif_to_numpy
from read_skeleton import load_NDskl
from skeleton_processing import SkeletonObject
from skeleton_network import skeleton_to_network 
import pickle


def skeleton_refinement(config_path):
        
    # Load parameters from config.yaml file
    with open(config_path) as f:
        config = yaml.safe_load(f)

    base_path = Path(config["path"])
    path_to_dir = str(base_path / config["path_to_dir"].strip("/"))  + "/"
    path_to_output = str(base_path / config["path_to_output"].strip("/"))  + "/"

    image = config["image"]
    img , metadata = open_tif_to_numpy(path_to_dir + image, crop_factor= 1)


    pixel_spacing = config["pixel_spacing"]
    angle_threshold = config["angle_threshold"]
    length_threshold = config["length_threshold"]
    remove_broken_ends = config["remove_broken_ends"]
    remove_spurious_ends = config["remove_broken_ends"]
    remove_dangling_ends = config["remove_dangling_ends"]

    persistence_val = config["persistence_val"]
    smooth_val = config["smooth_val"]
    assemble_val = config["assemble_val"]
    trimBelow_val = config["trimBelow_val"]

    raw_skeleton_file = "processed_" + image + f".fits_c{persistence_val}.up.NDskl.BRK.S{smooth_val}.ASMB.TRIM.rmB.a.NDskl"

    # Load skeleton
    skeleton = load_NDskl(path_to_output + raw_skeleton_file) 
    print(f"Skeleton loaded from: {path_to_output}{raw_skeleton_file}")

    # Refine skeleton
    skel_obj = SkeletonObject(skeleton, pixel_spacing[:2]).skeleton_processing(
        angle_threshold=angle_threshold,
        length_threshold=length_threshold
    )

    if remove_broken_ends == True:
        skel_obj = skel_obj.broken_ends()

    if remove_spurious_ends == True:
        skel_obj = skel_obj.spurious_ends()

    skel_obj = skel_obj.assemble_filaments(angle_threshold = angle_threshold)

    if remove_dangling_ends == True:
        skel_obj.dangling_ends()

    print(f"Skeleton is refined succesfully.")

    graph = skeleton_to_network(skel_obj, img, pixel_to_um = pixel_spacing[:2])
    print(f"Conversion to graph network...")

    # Save graph object to pickle file
    print("Saving...")
    pickle.dump(graph, open(path_to_output + f"refined_GN_{image}_c{persistence_val}_S{smooth_val}_as{assemble_val}_trim{trimBelow_val}_athr{str(angle_threshold)}_lthr{str(length_threshold)}.pickle", 'wb'))  
    print("Graph network saved to: " + path_to_output + f"refined_GN_{image}_c{persistence_val}_S{smooth_val}_as{assemble_val}_trim{trimBelow_val}_athr{str(angle_threshold)}_lthr{str(length_threshold)}.pickle")
    


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    skeleton_refinement(args.config)

