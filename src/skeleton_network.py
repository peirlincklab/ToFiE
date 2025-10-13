import networkx as nx
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from scipy.integrate import quad
from scipy.optimize import curve_fit
from skeleton_processing import SkeletonObject 


def angle_between_outbound_fiber(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vector1 = np.linalg.norm(vec1)
    norm_vector2 = np.linalg.norm(vec2)
    
    cos_theta = dot_product / (norm_vector1 * norm_vector2)
    angle_rad = np.arccos(cos_theta)
    
    return angle_rad


def skeleton_to_network(skeleton_obj, image, pixel_to_um):

    assert isinstance(skeleton_obj, SkeletonObject)
    skeleton = skeleton_obj.skeleton


    '''
    2D: pixel_to_um = [xy]
    3D: pixel_to_um = [z,xy]
    '''

    df0 = skeleton[0]
    df1 = skeleton[1]
    df2 = skeleton[2]
    df3 = skeleton[3]

    # Determine the nodes from the skeleton
    node1_index = df1.cp1.values
    node1 = df0.loc[node1_index]
    node2_index = df1.cp2.values
    node2 = df0.loc[node2_index]

    nodes_unique_index = np.unique(np.concatenate((node1_index, node2_index)))
    nodes = df0
    nodes["original_id"] = nodes.index
    nodes = nodes.loc[nodes_unique_index]

    # Determine the edges
    links = {}
    links["source"] = node1_index
    links["target"] = node2_index 


    if "z" not in df0.columns:
        assert (type(pixel_to_um) == list), "pixel_to_um input is a list specifiying the lateral pixel size"

        # Compute the node coordinates    
        nodes["x_um"] = nodes["x"] * pixel_to_um[0]
        nodes["y_um"] = nodes["y"] * pixel_to_um[0]
        dic_nodes = nodes.set_index("original_id")[["x", "y", "x_um","y_um", "field_value"]].T.to_dict('dict')

        # Combine all node attributes into dictionary
        node_attributes = []

        for n,d in dic_nodes.items():
            node_attributes.append((n,d))

        # Compute the edge length, and orientation
        links_df = pd.DataFrame.from_dict(links)

        edge_length=[]
        angle = [] 

        for p1,p2 in zip (nodes.loc[node1_index][["x_um","y_um"]].values, nodes.loc[node2_index][["x_um","y_um"]].values):
            
            # Compute the eucldiean distance from node to node as the edge length
            euclid_dist = np.linalg.norm(p1-p2)
            edge_length.append(euclid_dist)
            vector = p1-p2

            # Determine the azimuthal angle of the edge in radians
            angle_rad = math.atan2(vector[1],vector[0]) # counter-clockwise angle starting at x axis

            if angle_rad < -np.pi/2:
                angle_rad = angle_rad + np.pi
            elif angle_rad > np.pi/2:
                angle_rad = angle_rad - np.pi

            # angle_rad = angle_rad - np.pi/2  #azimuthal angle in range [-90,90], with angle measured counterclockwise wrt to the vertical


            angle.append(angle_rad)

        links_df["edge_length_um"] = edge_length
        links_df["angle_azi"] = angle

        arc_length = []

        for i in df2.filament.unique():
            # Compute the arc length of a filament as the sum of distance between all sampling points
            sampling_points = df2.query(f"filament=={i}")[["x","y"]].values*pixel_to_um[0]
            arc = np.sum(np.linalg.norm(sampling_points[1:] - sampling_points[:-1], axis=1))
            arc_length.append(arc)

        links_df["arc_length_um"] = arc_length
        
        # Combine all edge attributes into dictionary
        edge_attributes = []  

        for edg, attr in links_df[["edge_length_um", "arc_length_um", "angle_azi"]].T.to_dict('dict').items():
            edge_attributes.append((links_df.source.iloc[edg], links_df.target.iloc[edg], attr))

        # Create an undirected graph with node and edge attributes
        G = nx.Graph()
        G.add_nodes_from(node_attributes)  
        G.add_edges_from(edge_attributes)

        dic_pos={}
        dic_pos = nodes[list("xy")].T.to_dict('list')

        G.graph["image_shape"] = image.shape
        G.graph["pixel_size_um"] = pixel_to_um

        # plt.figure(figsize=(5, 5))
        # nx.draw(G, node_size = 1, node_color = "red",edge_color = "black", width = 0.2, pos = dic_pos)


    if "z" in df0.columns:

        assert (len(pixel_to_um) == 2), "pixel_to_um input is a list specifiying the axial and lateral voxel size."

        # Compute the node coordinates 
        nodes["x_um"] = nodes["x"] * pixel_to_um[1]
        nodes["y_um"] = nodes["y"] * pixel_to_um[1]
        nodes["z_um"] = nodes["z"] * pixel_to_um[0]
        dic_nodes = nodes.set_index("original_id")[["x", "y", "z", "x_um","y_um", "z_um", "field_value"]].T.to_dict('dict')
        
        # Combine all node attributes into dictionary
        node_attributes = []

        for n,d in dic_nodes.items():
            node_attributes.append((n,d))

        # Compute the edge length, and orientation
        links_df = pd.DataFrame.from_dict(links)

        edge_length=[]
        angle_azimuth = []
        angle_polar = [] 

        for p1, p2 in zip (nodes.loc[node1_index][["x_um","y_um", "z_um"]].values, nodes.loc[node2_index][["x_um","y_um","z_um"]].values):

            # Compute the eucldiean distance from node to node as the edge length
            euclid_dist = np.linalg.norm(p1-p2)
            edge_length.append(euclid_dist)
            vector = p1-p2

            # Determine the azimuthal and polar angle of the edge in radians
            angle_azi = math.atan2(vector[1],vector[0]) # counter-clockwise angle starting at x axis
            angle_pol = math.atan2(np.sqrt(vector[0]**2 + vector[1]**2), vector[2])

            if angle_azi < -np.pi/2:
                angle_azi = angle_azi + np.pi
            elif angle_azi > np.pi/2:
                angle_azi = angle_azi - np.pi
            
            if angle_pol > np.pi:
                angle_pol = abs((angle_pol - np.pi))

            angle_pol = angle_pol - np.pi/2  #polar angle in range [-90,90], with angle measured counterclockwise wrt to the vertical

            angle_azimuth.append(angle_azi)
            angle_polar.append(angle_pol)

        links_df["edge_length_um"] = edge_length
        links_df["angle_azi"] = angle_azimuth
        links_df["angle_polar"] = angle_polar

        arc_length = []

        for i in df2.filament.unique():

            # Compute the arc length of a filament as the sum of distance between all sampling points
            sampling_points = df2.query(f"filament=={i}")[["x","y", "z"]].multiply({"x": pixel_to_um[1], 'y': pixel_to_um[1], 'z': pixel_to_um[0]}).values
            arc = np.sum(np.linalg.norm(sampling_points[1:]- sampling_points[:-1], axis=1))
            arc_length.append(arc)
        
        links_df["arc_length_um"] = arc_length

        # Combine all edge attributes into dictionary
        edge_attributes = []  

        for edg, attr in links_df[["edge_length_um", "arc_length_um", "angle_azi", "angle_polar"]].T.to_dict('dict').items():
            edge_attributes.append((links_df.source.iloc[edg], links_df.target.iloc[edg], attr))

        # Create an undirected graph with node and edge attributes
        G = nx.Graph()
        G.add_nodes_from(node_attributes)  
        G.add_edges_from(edge_attributes)

        dic_pos={}
        dic_pos = nodes[list("xy")].T.to_dict('list')

        G.graph["image_shape"] = image.shape
        G.graph["pixel_size_um"] = pixel_to_um

        # plt.figure(figsize=(5, 5))
        # nx.draw(G, node_size = 1, node_color = "red",edge_color = "black", width = 0.2, pos = dic_pos)

    return G

def network_descriptors(graph, datasetName, plot_histogram = False, plot_graph_measures = False):

    # Node valency 
    valency = []
    [valency.append(n[1]) for n in graph.degree()]
    valency_mask = np.array(valency)[np.where(np.array(valency)>2)]

    # Edge length 
    length = np.array(list(nx.get_edge_attributes(graph,'edge_length_um').values()))
    fil_length = np.array(list(nx.get_edge_attributes(graph,'arc_length_um').values()))

    # Cosine distribution
    cosine_angles = []
    cosines = []

    nodes = [node for node in graph.nodes()]
    n_0 = nodes[0]


    if graph.nodes(data=True)[n_0].get('z'):

        for node in graph.nodes():
            if len(graph.edges(node))>1:
                orig_node_pos = np.array([graph.nodes[node]["x_um"], graph.nodes[node]["y_um"], graph.nodes[node]["z_um"]])

                for ii in range(len(graph.edges(node))-1):
                    node_connected = list(graph.edges(node))[ii][1]
                    connected_node_pos = np.array([graph.nodes[node_connected]["x_um"], graph.nodes[node_connected]["y_um"], graph.nodes[node_connected]["z_um"]])
                    vector1 =  (connected_node_pos - orig_node_pos)

                    for iii in range(1,len(graph.edges(node))):
                        if ii !=  iii:
                            node_connected2 = list(graph.edges(node))[iii][1]
                            connected_node_pos2 = np.array([graph.nodes[node_connected2]["x_um"], graph.nodes[node_connected2]["y_um"], graph.nodes[node_connected2]["z_um"]])
                            vector2 = (connected_node_pos2 - orig_node_pos)

                            cosine = angle_between_outbound_fiber(vector1.astype(np.float64), vector2.astype(np.float64))

                            # To avoid issues with too parallel outgoing fibers, leading to numerical instability
                            if np.linalg.norm(vector1) * np.linalg.norm(vector2) < 1e-6 or not np.isfinite(cosine):
                                continue
                            
                            cosine_angles.append(cosine)
                            cosines.append(np.cos(cosine))
    else:

        for node in graph.nodes():
            if len(graph.edges(node))>1:
                orig_node_pos = np.array([[graph.nodes[node]["x_um"], graph.nodes[node]["y_um"]]])

                for ii in range(len(graph.edges(node))-1):
                    node_connected = list(graph.edges(node))[ii][1]
                    connected_node_pos = np.array([[graph.nodes[node_connected]["x_um"], graph.nodes[node_connected]["y_um"]]])
                    vector1 =  (connected_node_pos - orig_node_pos)[0]

                    for iii in range(1,len(graph.edges(node))):
                        if ii !=  iii:
                            node_connected2 = list(graph.edges(node))[iii][1]
                            connected_node_pos2 = np.array([[graph.nodes[node_connected2]["x_um"], graph.nodes[node_connected2]["y_um"]]])
                            vector2 = (connected_node_pos2 - orig_node_pos)[0]

                            cosine = angle_between_outbound_fiber(vector1.astype(np.float64), vector2.astype(np.float64))

                            # To avoid issues with too parallel outgoing fibers, leading to numerical issues and instability
                            if np.linalg.norm(vector1) * np.linalg.norm(vector2) < 1e-6 or not np.isfinite(cosine):
                                continue
                            
                            cosine_angles.append(cosine)
                            cosines.append(np.cos(cosine))


    # Edge orientation
    if graph.nodes(data=True)[n_0].get('z'):
        angles_azi = np.array(list(nx.get_edge_attributes(graph,'angle_azi').values())) # extract all edges angle attributes
        angles_polar = np.array(list(nx.get_edge_attributes(graph,'angle_polar').values()))
    else:
        angles_azi = np.array(list(nx.get_edge_attributes(graph,'angle_azi').values())) # extract all edges angle attributes
        angles_polar = None

    # Edge density
    total_length = np.sum(length)
    if graph.nodes(data=True)[n_0].get('z'):
        volume = np.prod(np.append(np.array((graph.graph["image_shape"][1:])) * graph.graph["pixel_size_um"][0], np.array((graph.graph["image_shape"][0])) * graph.graph["pixel_size_um"][1])) #um^3
        fiber_density = total_length / volume # um^-2
    else:
        area = np.prod(np.array((graph.graph["image_shape"][1:])) * graph.graph["pixel_size_um"][0])  #um^2
        fiber_density = total_length / area # um^-1

    values = {"total #edges": len(length),
              "avg_fiber_density": np.round(fiber_density, 2), 
              "mean_edge_length": np.round(np.mean(length),2), 
              "mean_fil_length": np.round(np.mean(fil_length), 2), 
              "mean_valency": np.round(np.mean(valency_mask),2), 
              "mean_cosine_angle": np.round(np.mean(cosine_angles)/np.pi,2)}

    params_val, params_length, params_cos, params_azi = histogram_fits(graph, valency, length, cosine_angles, angles_azi)

    parameters = {"geometric parameters (valency): ": np.round(params_val,2).tolist(),
                  "log normal parameters (edge length): ": np.round(params_length,2).tolist(),
                  "beta parameters (cosine angle): ": np.round(params_cos,2).tolist(),
                  "Von Mises parameters (azimuthal angle): ": np.round(params_azi,2).tolist() }


    # # Compute graph measures from NetworkX
    # graph_measure = {}

    # # Betweenness Centrality: how important is a node for information flow, number of shortest paths passing through it
    # betweenness = nx.betweenness_centrality(graph, normalized=True, weight="edge_length_um", endpoints=True)
    # node_color_betweenness = [betweenness[node] for node in graph.nodes]

    # # Closeness Centrallity: How close a node is to all other nodes
    # closeness = nx.closeness_centrality(graph, distance = "edge_length_um")
    # node_color_closeness = [closeness[node] for node in graph.nodes]

    # # Clustering coefficient: local connectivity or clustering of nodes within the network, tells you about the presence of tightly connected groups
    # clustering = nx.clustering(graph)
    # node_color_cluster = [clustering[node] for node in graph.nodes]

    # graph_measure["betweenness mean, std.: "] = [np.round(np.mean(node_color_betweenness),2), np.round(np.std(node_color_betweenness),2)]
    # graph_measure["closeness mean, std.: "] = [np.round(np.mean(node_color_closeness),2), np.round(np.std(node_color_closeness),2)]
    # graph_measure["clustering mean, std.: "] = [np.round(np.mean(node_color_cluster),2), np.round(np.std(node_color_cluster),2)]


    summary = values|parameters#|graph_measure
    print(summary)


    if not os.path.exists(datasetName):
        os.makedirs(datasetName)

    if plot_histogram == True:
        histogram_plot(valency, length, cosine_angles, angles_azi, params_val, params_length, params_cos, params_azi, datasetName)

    if plot_graph_measures == True:
        graph_measures_plot(graph, datasetName)
    

    # # Save average values, fitted parameters, graph measures
    # with open(datasetName +"_summary.txt", 'w') as f:
    #     for key in summary:
    #         f.write(f"{key} {summary[key]}\n")
    #     print("Average network values, fitted parameters, graph measures are saved to " + datasetName +"_summary.txt")


    # # Save the valency, length, cosine angle and azimuthal angle distributions
    # name = ["valency", "length", "cosine_angles", "angles_azi"]
    # for i, distributions in enumerate([valency, length, cosine_angles, angles_azi]):
    #     n = name[i]

    #     with open(datasetName + f"_{n}.txt", 'w') as f:
    #         values_str = [str(val) + '\n' for val in distributions]
    #         f.writelines(values_str)
        
    #     print("Distributions are saved to " + datasetName + f"_{n}.txt")

    
    return valency, length, cosine_angles, angles_azi, angles_polar, summary


def histogram_fits(graph, valency, length, cosine_angles, angles_azi):

    # Fit shifted geometric distribution to the node valency distribution
    valency_mask = np.array(valency)[np.where(np.array(valency)>2)]
    hist, edges = np.histogram(valency_mask, bins= np.arange(3, 7), density=True)
    centers = (edges[:-1] + edges[1:]) / 2

    print( edges[:-1])

    params_val, covariance = curve_fit(shifted_geometric, centers, hist, bounds=(3,7))  # parameters are z
    print( "z = ", params_val[0])


    # Log normal fit to edge length distribution
    hist, edges = np.histogram(length, bins=np.linspace(0, 20, 40), density=True)
    centers = (edges[:-1] + edges[1:]) / 2

    params_length, covariance = curve_fit(log_normal, centers, hist, p0=[3, 2])  # parameters are L, and variance s
    print( "L = ", params_length[0], "v = ", params_length[1])


    # Fit beta distribution to normalized cosine angles 
    norm_cosine_angles = np.array(cosine_angles)/np.pi
    hist, edges = np.histogram(norm_cosine_angles, bins=np.linspace(0, 1, 50), density=True)
    centers = (edges[:-1] + edges[1:]) / 2

    params_cos, covariance = curve_fit(beta, centers, hist, p0=[1,1], bounds=([0,0],[1000,1000]))  # parameters are alpha, beta

    # Univariate Von Mises fitting to edge azimuthal orientation
    nodes = [node for node in graph.nodes()]
    n_0 = nodes[0]

    if graph.nodes(data=True)[n_0].get('z'):
        abins = np.linspace(-np.pi/2, np.pi/2, 31)
        hist, edges = np.histogram(angles_azi, bins=abins, density = True, weights = length)
        hist_anistropic  = np.array(hist) - min(hist)
        total_area = np.sum(hist_anistropic * np.diff(edges))
        hist_anistropic_normalized =  hist_anistropic / total_area # renormalized anisotropic histogram fraction 
        centers = (edges[:-1] + edges[1:]) / 2
        Piso =  np.sum(min(hist) * np.diff(edges)) #area underneath the histogram

        # parameters are theta0 and k, theta0 indicates the mean of the distribution and k represents the concentration parameter
        # To fit multiple peaks, add the intiial guess for each parameter for each peak

        params_azi, covariance = curve_fit(multi_vonmises, centers, hist_anistropic_normalized, p0 = [0,1], bounds = ([-np.pi/2,0], [np.pi/2, 20]))  
        print(fr"P_isotropic = {np.round(Piso, 2)}, P_anisotropic = {np.round(1 - Piso, 2)}")

    else:
        abins = np.linspace(-np.pi/2, np.pi/2, 31)
        hist, edges = np.histogram(angles_azi, bins=abins, density = True, weights = length)
        hist_anistropic  = np.array(hist) - min(hist)
        total_area = np.sum(hist_anistropic * np.diff(edges))
        hist_anistropic_normalized =  hist_anistropic / total_area # renormalized anisotropic histogram fraction 
        centers = (edges[:-1] + edges[1:]) / 2
        Piso =  np.sum(min(hist) * np.diff(edges))   #area underneath the histogram

        # parameters are theta0 and k, theta0 indicates the mean of the distribution and k represents the concentration parameter
        # To fit multiple peaks, add the intiial guess for each parameter for each peak

        params_azi, covariance = curve_fit(multi_vonmises, centers, hist_anistropic_normalized, p0 = [0,0.5], bounds = ([-np.pi/2,0], [np.pi/2, 20]))  
        print(fr"$P_{{isotropic}}$ = {np.round(Piso, 2)}, $P_{{anisotropic}}$ = {np.round(1 - Piso, 2)}")

    return params_val, params_length, params_cos, params_azi


def histogram_plot(valency, length, cosine_angles, angles_azi, params_val, params_length, params_cos, params_azi, figName):

    valency_mask = np.array(valency)[np.where(np.array(valency)>2)]
    val_unique = np.unique(valency_mask)
    hist, edges = np.histogram(valency_mask, bins=np.arange(3, 7), density=True)
    centers = (edges[:-1] + edges[1:]) / 2
    x_fit = np.linspace(edges[0], edges[-1], 50)
    y_fit = shifted_geometric(x_fit, *params_val)
    print("R^2 = ", r_squared(hist, shifted_geometric(edges[:-1], *params_val)))

    # Plot valency distribution
    plt.figure(figsize=(16,5),dpi=400)
    plt.subplot(1,4,1)
    plt.hist(valency_mask, bins=np.arange(3, 7), facecolor='lightgray', alpha = 0.8, density=True)#, label = "Node degree")
    plt.plot(x_fit, y_fit, label='Shifted geometric fit', color='magenta',  linewidth=1.5)
    plt.plot([], [], ' ', label=rf"$\overline{{z}}$: {np.round(params_val[0],3)}")
    plt.plot([], [], ' ', label=rf"$R^{{2}}$: {r_squared(hist, shifted_geometric(edges[:-1], *params_val))}")
    plt.xlabel("Node valency z")
    plt.ylabel(r'$f_{geometric}$( z; $\overline{z})$')
    plt.legend().get_frame().set_linewidth(0.0)
    plt.minorticks_on()
    plt.tick_params(direction='in', which= "both", top = True, right = True)
    plt.tight_layout()


    hist, edges = np.histogram(length, bins=np.linspace(0, 20, 40), density=True)
    centers = (edges[:-1] + edges[1:]) / 2
    x_fit = np.linspace(edges.min(), edges.max(), 100)
    y_fit = log_normal(x_fit, *params_length)
    print("R^2 = ",r_squared(hist,  log_normal(centers, *params_length)))

    # Plot edge length distribution
    plt.subplot(1,4,2)
    plt.hist(length,bins=np.linspace(0, 20, 40), density=True,  facecolor='lightgray', alpha = 0.8)#, label = "Edge length")
    plt.plot(x_fit, y_fit, label='Log-normal fit', color='magenta',  linewidth=1.5)
    plt.plot([], [], ' ', label=fr"$\overline{{l}}$: {np.round(params_length[0],3)}, v: {np.round(params_length[1],3)}")
    plt.plot([], [], ' ', label=rf"$R^{{2}}$: {r_squared(hist,  log_normal(centers, *params_length))}")
    plt.ylabel(r'$f_{log-normal}( l; \overline{l}, v)$')
    plt.xlabel("Edge length $l$ ($\mu$m)")
    plt.legend().get_frame().set_linewidth(0.0)
    plt.minorticks_on()
    plt.tick_params(direction='in', which= "both", top = True, right = True)
    plt.tight_layout()

    norm_cosine_angles = np.array(cosine_angles)/np.pi
    hist, edges = np.histogram(norm_cosine_angles, bins=np.linspace(0, 1, 50), density=True)
    centers = (edges[:-1] + edges[1:]) / 2
    x_fit = np.linspace(edges.min(), edges.max(), 100)
    y_fit = beta(x_fit, *params_cos)
    print("R^2 = ", r_squared(hist,  beta(centers, *params_cos)))

    # Plot cosine distribution
    plt.subplot(1,4,3)
    plt.hist(norm_cosine_angles, bins=np.linspace(0, 1, 50), density=True, facecolor='lightgray', alpha = 0.8)#, label = "Edge cosines")
    plt.plot(x_fit, y_fit, label='Beta fit', color='magenta',  linewidth=1.5)
    plt.plot([], [], ' ', label=fr"$\alpha$: {np.round(params_cos[0],3)}, $\beta$: {np.round(params_cos[1],3)}")
    plt.plot([], [], ' ', label=rf"$R^{{2}}$: {r_squared(hist,  beta(centers, *params_cos))}")
    plt.ylabel(r'$f_{beta}$($\delta$; $\alpha$, $\beta$)')
    plt.xlabel(r"Normalized cosine angle $\delta$")
    plt.legend().get_frame().set_linewidth(0.0)
    plt.minorticks_on()
    plt.tick_params(direction='in', which= "both", top = True, right = True)
    plt.tight_layout()

    abins = np.linspace(-np.pi/2, np.pi/2, 31)
    hist, edges = np.histogram(angles_azi, bins=abins, density = True, weights=length)
    hist_anistropic  = np.array(hist) - min(hist)
    total_area = np.sum(hist * np.diff(edges))
    total_area_a = np.sum(hist_anistropic * np.diff(edges))
    hist_anistropic_normalized =  hist_anistropic / total_area_a # renormalized anisotropic histogram fraction 
    centers = (edges[:-1] + edges[1:]) / 2
    x_fit = np.linspace(centers.min(), centers.max(), 50)
    y_fit = multi_vonmises(x_fit, *params_azi) * (total_area_a/total_area)  # normalizing back to total_area_a<1

    print("R^2 = ", r_squared(hist_anistropic_normalized,  multi_vonmises(centers, *params_azi)))
    Piso =  np.sum(min(hist) * np.diff(edges)) #area underneath the histogram

    # Plot azimuthal distribution
    plt.subplot(1,4,4)
    plt.hist(angles_azi, bins=np.linspace(-np.pi/2, np.pi/2, 31), density=True, facecolor='lightgray', alpha = 0.8, weights = length) #label = "Edge azimuthal angle",
    plt.hlines(min(hist),min(angles_azi), max(angles_azi),"white")
    plt.plot(x_fit, y_fit + min(hist),label=f"Von Mises fit", color='magenta', linewidth=1.5) 
    plt.plot([], [], ' ', label=fr"$\theta_{0}$: {np.round(params_azi[0],3)}, K: {np.round(params_azi[1],3)}")
    plt.plot([], [], ' ', label=fr"$P_{{anisotropic}}$ = {np.round(1-Piso, 3)}")
    plt.plot([], [], ' ', label=rf"$R^{{2}}$: {r_squared(hist_anistropic_normalized,  multi_vonmises(centers, *params_azi))}")
    plt.xlabel(r"Azimuthal angle $\theta$ (rad)")
    plt.ylabel(r'$f_{vonMises}$($\theta$; $\theta_{0}$, K)')
    plt.legend(loc = "best").get_frame().set_linewidth(0.0)
    plt.minorticks_on()
    plt.tick_params(direction='in', which= "both", top = True, right = True)
    plt.tight_layout()

    plt.savefig(figName + "_distributions.png")
    plt.show()


def save_graph_network(graph, filename):
    with open(filename +"_nodes.txt", 'w') as f:
        # Save node coordinates (µm)
        for node, data in graph.nodes(data=True):
            f.write(f"{node} {data['x_um']} {data['y_um']} {data['z_um']}\n")
    
    with open(filename +"_edges.txt", 'w') as f:
        # Save edges 
        for u, v in graph.edges():
            f.write(f"{u} {v}\n")

    print("Node coordinates and edges of the graph are saved to " + filename +"_nodes.txt" + ", " + filename + "_edges.txt")

def graph_measures_plot(graph, figName):

    dic_pos = {}
    for node, attr in graph.nodes(data=True):
        dic_pos[node] = [attr['x_um'], attr['y_um']]

    # Betweenness Centrality: how important is a node for information flow, number of shortest paths passing through it
    betweenness = nx.betweenness_centrality(graph, normalized=True, weight="edge_length_um", endpoints=True)
    node_color_betweenness = [betweenness[node] for node in graph.nodes]

    # Closeness Centrallity: How close a node is to all other nodes
    closeness = nx.closeness_centrality(graph, distance = "edge_length_um")
    node_color_closeness = [closeness[node] for node in graph.nodes]

    # Clustering coefficient: local connectivity or clustering of nodes within the network, tells you about the presence of tightly connected groups
    clustering = nx.clustering(graph)
    node_color_cluster = [clustering[node] for node in graph.nodes]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi = 200)

    nx.draw(graph, node_size=30, node_color = node_color_betweenness, edge_color="black", width=0.2, pos= dic_pos, ax=axes[0], cmap='magma')
    axes[0].set_title(rf'$\overline{{x}}$: {np.round(np.mean(node_color_betweenness),2)}, $\sigma$: {np.round(np.std(node_color_betweenness),2)}', y=-0.01)

    nx.draw(graph, node_size=30, node_color = node_color_closeness, edge_color="black", width=0.2, pos= dic_pos, ax=axes[1], cmap='magma')
    axes[1].set_title(rf'$\overline{{x}}$: {np.round(np.mean(node_color_closeness),2)}, $\sigma$: {np.round(np.std(node_color_closeness),2)}', y=-0.01)

    nx.draw(graph, node_size = 30, node_color = node_color_cluster, edge_color = "black", width = 0.2, pos = dic_pos, ax=axes[2], cmap='magma')
    axes[2].set_title(rf'$\overline{{x}}$: {np.round(np.mean(node_color_cluster),2)}, $\sigma$: {np.round(np.std(node_color_cluster),2)}', y=-0.01)

    for ax, node_color, title in zip(axes, [node_color_betweenness, node_color_closeness, node_color_cluster], ['Betweenness','Closeness', 'Clustering']):
        sm = plt.cm.ScalarMappable(norm=plt.Normalize(vmin=min(node_color), vmax=max(node_color)), cmap='magma')
        sm.set_array([]) 
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical',fraction=0.05)
        cbar.set_label(f'{title}')

    plt.tight_layout()
    plt.savefig(figName + "_graphMeasures.png")
    plt.show()

    return 

## Distributions for fitting

def pareto(x, a):
    xm=3
    return a*(xm**a)/(x**(a+1))

def shifted_geometric(x, z):
    q = 1/(z-2)
    return q*(1-q)**(x-3)

def log_normal(x, L, v):
    #v = (s/L)**2
    zeta = np.log(v + 1)
    lamb = np.log(L) - (zeta**2)/2
    
    return 1/(x *np.sqrt(2*np.pi* zeta**2))* np.exp(- ((lamb-np.log(x))**2) / (2*zeta**2))

def truncated_pow_series(x, b1, b2, b3):
    return b1*((1-x)**1) + b2*((1-x)**3) + b3*((1-x)**5)

def beta(x, alpha, beta):
    B = math.gamma(alpha)*math.gamma(beta)/math.gamma(alpha+beta)
    return x**(alpha-1) * (1-x)**(beta-1)/ B

def multi_vonmises(x, *params):  # For multi-peak 2D angular histograms

        n_components = len(params) // 2
        result = np.zeros_like(x)

        for i in range(n_components):
            theta0 = params[2*i]
            m = params[2*i + 1]
            result += vonmises_distribution(x, theta0, m)

        return result

def vonmises_distribution(x, theta0, k):
    
    integrand = lambda t: 1/(2*np.pi) * np.exp(k * np.cos(t))

    integral_I, _ = quad(integrand, 0, 2*np.pi)

    return 1/(np.pi*integral_I) * np.exp(k * np.cos(2*(x-theta0)))    #  adjusted to make distribution periodic over Pi instead of 2Pi

def bivariate_vonmises(X, theta0, phi0, k1,k2):

    x,y = X

    integrand_erf = lambda t: (2/np.sqrt(np.pi))* np.exp(-t**2)

    integral_erf, _ = quad(integrand_erf, 0, np.sqrt(2*k2))

    integrand_I = lambda t: (1/np.pi) * np.exp(k1 * np.cos(t))

    integral_I, _ = quad(integrand_I, 0, np.pi)

    return (np.exp(k1*np.cos(2*(x-theta0)))/integral_I) * 2 * np.sqrt(2*k2/np.pi) *  (np.exp( k2*(np.cos(2*(y+phi0))-1)) / integral_erf)


def r_squared(y_true, y_pred):

    y_mean = np.mean(y_true)
    sst = np.sum((y_true - y_mean)**2)
    sse = np.sum((y_true - y_pred)**2)    
    r_squared = 1 - (sse / sst)

    if sst == 0:
        r_squared = 1.0
   
    return np.round(r_squared,3)
