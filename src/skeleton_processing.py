import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import pickle


def filament_breakdown_node_correction(skeleton):
    
    if "z" in skeleton[0].columns: # 3D skeleton
        endpoint_cps_idx = pd.concat([skeleton[1]["cp1"], skeleton[1]["cp2"]]).unique()
        x_cp = skeleton[0].loc[endpoint_cps_idx].x.values
        y_cp = skeleton[0].loc[endpoint_cps_idx].y.values
        z_cp = skeleton[0].loc[endpoint_cps_idx].z.values
        endpoint_cps_coord = list(zip(x_cp, y_cp, z_cp))
        count = 0
        filament_idx = 0
        new_fil_info = []
        sampling_info = []

        # Search over each original filaments
        for i in skeleton[2].filament.unique():
            # print ("filament index: ", i )

            # Make sure there is no duplicates in a filament's sampling points
            filtered_points = skeleton[2].query(f"filament=={i}").drop_duplicates(subset=['x', 'y', "z"])
            x_points = filtered_points.x.values
            y_points = filtered_points.y.values
            z_points = filtered_points.z.values
            
            filament_points = list(zip(x_points[1:-1], y_points[1:-1], z_points[1:-1]))

            filament_cp1, filament_cp2 = skeleton[1].loc[i].cp1, skeleton[1].loc[i].cp2
            intermediate_cps = [filament_cp1]
            cp_samp_idx = [0]

            # Search over each filament's sampling points 

            for fil_point_idx, fil_point in enumerate(filament_points):

                # Check if there are critical end points within the filament, if so save the critical points index and position within the filament
                if fil_point in endpoint_cps_coord:
                    cp_end_idx = endpoint_cps_coord.index(fil_point)
                    cp_idx = endpoint_cps_idx[cp_end_idx] 
                    intermediate_cps.append(cp_idx)   # cp index in skeleton[0]
                    cp_samp_idx.append(fil_point_idx + 1)  # cp index in skeleton[2] for the filament sampling points
            
            intermediate_cps.append(filament_cp2)
            cp_samp_idx.append(len(x_points))

            # For each critical point found in a single filament, construct a new filament starting and ending at a critical point, which contains no critcial point within itself
            # print("intermediate critical point index: ", cp_samp_idx, intermediate_cps)
            
            for ii in range(len(intermediate_cps)-1): 
                sampling_points = list(zip(x_points, y_points, z_points))
                nsamp = len(sampling_points[cp_samp_idx[ii]:cp_samp_idx[ii+1]])
                cp1, cp2 = intermediate_cps[ii], intermediate_cps[ii+1]
                new_fil_id = filament_idx

                # Save the new filament's information
                new_fil_info.append([new_fil_id, cp1, cp2, nsamp])
                sampling = skeleton[2].query(f"filament=={i}").iloc[cp_samp_idx[ii]:cp_samp_idx[ii+1]+1]
        
                # Save the new filament's sampling point information
                for iii in range(len(sampling.x)):
                    sampling_info.append([filament_idx, sampling.x.values[iii], sampling.y.values[iii], sampling.z.values[iii], sampling.field_value.values[iii]])

                filament_idx +=1

        # Create new dataframe replicating the structure of skeleton[1], skeleton[2]
        df1 = pd.DataFrame(new_fil_info, columns =['f_id', 'cp1', 'cp2', 'nsamp'], dtype = int)
        df2 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y','z','field_value'], dtype = float).astype({"filament":int, "field_value":int})

        # Update the connectivity or nfil of the critical points in the critical points dataframe, replicating the structure of skeleton[0]
        df0 = skeleton[0]
        cp_info = {}

        for i in endpoint_cps_idx:  # count how many times a CP appears, and update the connections of endpoint CP
            new_nfil = len(df1.query(f"cp1=={i}").cp1.tolist()) + len(df1.query(f"cp2=={i}").cp2.tolist())
            df0.loc[i, "nfil"] = new_nfil
            
            destination =  list(df1.query(f"cp1 == {i}").cp2.values)
            fill_id = list(df1.query(f"cp1 == {i}").f_id.values)
            destination.extend( df1.query(f"cp2 == {i}").cp1.values)
            fill_id.extend(df1.query(f"cp2 == {i}").f_id.values)

            cp_info[i] = {'cp_idx': i, 'destcritid': destination, 'fillId': fill_id}
        
        df3 = pd.DataFrame.from_dict(cp_info, orient='index')

    else: # 2D skeleton

        endpoint_cps_idx = pd.concat([skeleton[1]["cp1"], skeleton[1]["cp2"]]).unique()
        x_cp = skeleton[0].loc[endpoint_cps_idx].x.values
        y_cp = skeleton[0].loc[endpoint_cps_idx].y.values
        endpoint_cps_coord = list(zip(x_cp, y_cp))
        count = 0
        filament_idx = 0
        new_fil_info = []
        sampling_info = []

        # Search over each original filaments
        for i in skeleton[2].filament.unique():
            # print ("filament index: ", i )

            # make sure there is no duplicates in a filament's sampling points
            filtered_points = skeleton[2].query(f"filament=={i}").drop_duplicates(subset=['x', 'y'])
            x_points = filtered_points.x.values
            y_points = filtered_points.y.values
            
            filament_points = list(zip(x_points[1:-1], y_points[1:-1]))

            filament_cp1, filament_cp2 = skeleton[1].loc[i].cp1, skeleton[1].loc[i].cp2
            intermediate_cps = [filament_cp1]
            cp_samp_idx = [0]

            # Search over each filament's sampling points 
            for fil_point_idx, fil_point in enumerate(filament_points):

                # Check if there are critical end points within the filament, if so save the critical points index and position within the filament
                if fil_point in endpoint_cps_coord:
                    cp_end_idx = endpoint_cps_coord.index(fil_point)
                    cp_idx = endpoint_cps_idx[cp_end_idx] 
                    intermediate_cps.append(cp_idx)   # cp index in skeleton[0]
                    cp_samp_idx.append(fil_point_idx + 1)  # cp index in skeleton[2] for the filament sampling points
            
            intermediate_cps.append(filament_cp2)
            cp_samp_idx.append(len(x_points))

            # For each critical point found in a single filament, construct a new filament starting and ending at a critical point, which contains no critcial point within itself
            # print("intermediate critical point index: ", cp_samp_idx, intermediate_cps)
            
            for ii in range(len(intermediate_cps)-1): 
                sampling_points = list(zip(x_points, y_points))
                nsamp = len(sampling_points[cp_samp_idx[ii]:cp_samp_idx[ii+1]])
                cp1, cp2 = intermediate_cps[ii], intermediate_cps[ii+1]
                new_fil_id = filament_idx

                # Save the new filament's information
                new_fil_info.append([new_fil_id, cp1, cp2, nsamp])
    

                sampling = skeleton[2].query(f"filament=={i}").iloc[cp_samp_idx[ii]:cp_samp_idx[ii+1]+1]
        
                # Save the new filament's sampling point information
                for iii in range(len(sampling.x)):
                    sampling_info.append([filament_idx, sampling.x.values[iii], sampling.y.values[iii], sampling.field_value.values[iii]])

                filament_idx +=1

        # Create new dataframe replicating the structure of skeleton[1], skeleton[2]
        df1 = pd.DataFrame(new_fil_info, columns =['f_id', 'cp1', 'cp2', 'nsamp'], dtype = int)
        df2 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y', 'field_value'], dtype = float).astype({"filament":int, "field_value":int})

        # Update the connectivity or nfil of the critical points in the critical points dataframe, replicating the structure of skeleton[0]
        df0 = skeleton[0]
        cp_info = {}

        for i in endpoint_cps_idx:  # count how many times a CP appears, and update the connections of endpoint CP
            new_nfil = len(df1.query(f"cp1=={i}").cp1.tolist()) + len(df1.query(f"cp2=={i}").cp2.tolist())
            df0.loc[i, "nfil"] = new_nfil
            
            destination =  list(df1.query(f"cp1 == {i}").cp2.values)
            fill_id = list(df1.query(f"cp1 == {i}").f_id.values)
            destination.extend( df1.query(f"cp2 == {i}").cp1.values)
            fill_id.extend(df1.query(f"cp2 == {i}").f_id.values)

            cp_info[i] = {'cp_idx': i, 'destcritid': destination, 'fillId': fill_id}
        
        df3 = pd.DataFrame.from_dict(cp_info, orient='index')

    skeleton_refined = (df0,df1,df2,df3)

    return skeleton_refined


def clean_short_filaments(skeleton, threshold_npoints):

    df0 = skeleton[0]
    df1 = skeleton[1]
    df2 = skeleton[2]
    df3 = skeleton[3]

    rm_fil_idx = []

    if "z" in df0.columns: # 3D skeleton

        # while loop to repeatedly remove short filaments
        while (df2.groupby("filament").size() < threshold_npoints).any():

            print("Loop #")
            prev_remaining = len(rm_fil_idx)
            rm_fil_idx = []

            # Iteratively remove filaments from smallest to largest

            for threshold in np.arange(1, threshold_npoints+1):

                # filaments = df2.filament.unique()
                
                filaments = df2.groupby("filament").size()[lambda x: x <= threshold].index

                # Iterate over each exisiting filament
                for i in filaments:

                    # if len(df2.query(f"filament=={i}").x.values) <= threshold:
                        
                    rm_fil_idx.append(i)

                    cp1, cp2 = df1.query(f"f_id == {i}").cp1.values[0], df1.query(f"f_id == {i}").cp2.values[0]
                    # print("cp1 and cp2: ", cp1, cp2)
                    connection_type = [len(df3.loc[cp1].destcritid),len(df3.loc[cp2].destcritid)]
                    # print ("filament index: ", i, "connection type: ", connection_type)

                    if connection_type != [len(np.unique(df3.loc[cp1].destcritid)),len(np.unique(df3.loc[cp2].destcritid))]:  # Pass over breaking down of loops
                        continue
            
                    if 1 in connection_type and 2 not in connection_type: # Remove the 1-connected CP
                        
                        # Find index of 1-connected CP and other connected CP
                        cp_1_connect, cp_other = [cp1, cp2] if connection_type[0] == 1 else [cp2, cp1]  

                        # Remove 1-connected CP from critical points info
                        df3 = df3.drop(df3.query(f"cp_idx == {cp_1_connect}").index) 

                        # Update the CP and filament conections of the other CP
                        df3.loc[cp_other].destcritid.remove(cp_1_connect) 
                        df3.loc[cp_other].fillId.remove(i)

                        # Remove the short filament from the filament info
                        df1 = df1.drop(df1.query(f"f_id == {i}").index)  

                        # Remove sampling points for filament i 
                        df2 = df2.drop(df2.query(f"filament == {i}").index)  


                        if connection_type == [1,1]:
                            # Remove the other 1-connected CP from critical points info
                            df3 = df3.drop(df3.query(f"cp_idx == {cp_other}").index)
                            # Set the connections of the other CP to zero.
                            df0.at[cp_other, 'nfil'] = 0
                        else:
                            # Decrease the connections of the other CP
                            df0.at[cp_other, 'nfil'] = df0.at[cp_other, 'nfil'] - 1 


                    if all(v >= 3 for v in connection_type): # Two critical points both with valency >=3
                        
                        # Determine whcih CP to remove and which to merge into based on their field value
                        cp_to_merge, cp_to_remove = [cp1, cp2] if df0.loc[cp1].field_value > df0.loc[cp2].field_value else [cp2, cp1]

                        # Find all filaments connected to cp_to_remove to grow, besides the filament to be removed
                        filament_to_grow = df3.loc[cp_to_remove].fillId
                        filament_to_grow.remove(i)
                    
                        # Sampling points to grow the filaments by
                        x, y, z, field = [df2.query(f"filament == {i}").x.values.tolist(), df2.query(f"filament == {i}").y.values.tolist(), df2.query(f"filament == {i}").z.values.tolist(), df2.query(f"filament == {i}").field_value.values.tolist()]

                        sampling_info = []
                        cp_starts = []

                        for fil in filament_to_grow:
                            for ii in range (len(x)):
                                sampling_info.append([fil, x[ii], y[ii], z[ii], field[ii]])

                            # Update the endpoint of the merged filament and record the cp of the start of the filaments
                            if df1.loc[fil].cp1 == cp_to_remove:
                                df1.loc[fil].cp1 = cp_to_merge
                                cp_starts.append(df1.loc[fil].cp2)
                            else:
                                df1.loc[fil].cp2 = cp_to_merge
                                cp_starts.append(df1.loc[fil].cp1)
                            
                            # Update the length of the grown filaments
                            df1.at[fil,"nsamp"] = df1.at[fil,"nsamp"] + len(x) 

                        # Update the sampling points associated to the grown filaments
                        df22 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y', 'z', 'field_value'], dtype = float).astype({"filament":int, "field_value":int})
                        df2 = pd.concat([df2,df22], ignore_index=True)  # *reset index of rows after concatenating to prevent multiple rows with the same index

                        # Remove the original short filament
                        df2 = df2.drop(df2.query(f"filament == {i}").index)
                        df1 = df1.drop(df1.query(f"f_id == {i}").index)
                        
                        # Remove the cp_to remove
                        df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)

                        # Update the endpoints of the grown filaments
                        df3.loc[cp_to_merge].destcritid.remove(cp_to_remove)
                        df3.loc[cp_to_merge].fillId.remove(i)

                        for c, cp in enumerate(cp_starts):
                            id = df3.loc[cp].destcritid.index(cp_to_remove)
                            df3.loc[cp].destcritid[id] = cp_to_merge
                            df3.at[cp_to_merge, 'destcritid'].append(cp)
                            df3.at[cp_to_merge, 'fillId'].append(filament_to_grow[c])

                        # Update connectivity of the merged critical point, and removed cp
                        df0.at[cp_to_merge, 'nfil'] = df0.at[cp_to_merge, 'nfil'] + len(cp_starts) - 1
                        df0.at[cp_to_remove, 'nfil']  = 0
                    
                    if 2 in connection_type:

                        if any(v >= 3 for v in connection_type): # Merge the short filament by the 2-connected CP
                            cp_2_connect, cp_other = [cp1, cp2] if connection_type[0] == 2 else [cp2, cp1]
                            cp_end = cp_other
                            cp_to_remove = cp_2_connect
                            filament_to_grow = [f for f in df3.query(f"cp_idx == {cp_to_remove}").fillId.values[0] if f!=i][0]
                            cp_start = [c for c in df3.at[cp_to_remove,"destcritid"] if c!= cp_end][0]

                        if connection_type  == [2,2]:
                            cp_start = [c for c in df3.at[cp1,"destcritid"] if c!= cp2][0]
                            cp_end = [c for c in df3.at[cp2,"destcritid"] if c!= cp1][0]

                            vectors = []

                            # Check which neighbouring filament shares the closest orientation with the short filament
                            for pair in [[cp_start,cp1],[cp1,cp2], [cp2,cp_end]]:
                                cp1_coord, cp2_coord = [df0.loc[pair[0], ['x','y', 'z']], df0.loc[pair[1], ['x','y','z']]]
                                vector = cp2_coord - cp1_coord
                                vectors.append(vector)
                        
                            if angle_between_vectors(vectors[1], vectors[0]) < angle_between_vectors(vectors[2], vectors[1]) :
                                cp_to_remove = cp1
                                cp_end = cp2
                                filament_to_grow = [c for c in df3.at[cp1,"fillId"] if c!= i][0]
                            else:
                                cp_to_remove = cp2
                                cp_start = cp_end
                                cp_end = cp1
                                filament_to_grow = [c for c in df3.at[cp2,"fillId"] if c!= i][0]
                            

                        if sorted(connection_type) == sorted([1,2]):
                            cp_1_connect, cp_2_connect = [cp1, cp2] if connection_type[0] == 1 else [cp2, cp1]
                            cp_end = cp_1_connect
                            cp_to_remove = cp_2_connect
                            cp_start = [c for c in df3.at[cp_to_remove,"destcritid"] if c!= cp_end][0]

                            filament_to_grow = [c for c in df3.at[cp_to_remove,"fillId"] if c!= i][0]


                        x, y, z, field = [df2.query(f"filament == {i}").x.values.tolist(), df2.query(f"filament == {i}").y.values.tolist(), df2.query(f"filament == {i}").z.values.tolist(), df2.query(f"filament == {i}").field_value.values.tolist()]
                        sampling_info = []

                        # Grow the neighbouring filament by the short filament points
                        for ii in range (len(x)):
                            sampling_info.append([filament_to_grow, x[ii], y[ii], z[ii], field[ii]])

                        df22 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y', 'z', 'field_value'], dtype = float).astype({"filament":int, "field_value":int})
                        df2 = pd.concat([df2,df22], ignore_index=True)  # *reset index of rows after concatenating to prevent multiple rows with the same index
                        
                        # Remove the original short filament
                        df2 = df2.drop(df2.query(f"filament == {i}").index)
                        df1 = df1.drop(df1.query(f"f_id == {i}").index)
                        
                        # Change endpoint of filament to grow
                        if df1.loc[filament_to_grow].cp1 == cp_to_remove:
                            df1.at[filament_to_grow,"cp1"] = cp_end
                        else:
                            df1.at[filament_to_grow,"cp2"] = cp_end   
                        
                        # Update the length of the merged filament
                        df1.at[filament_to_grow,"nsamp"] = df1.at[filament_to_grow,"nsamp"] + len(x)

                        # Update the endpints, filaments of cp_start and cp_end
                        df3.at[cp_end, "destcritid"].remove(cp_to_remove)
                        df3.at[cp_end, "fillId"].remove(i)
                        df3.at[cp_end, "fillId"].append(filament_to_grow)
                        df3.at[cp_end, "destcritid"].append(cp_start)

                        idx = df3.loc[cp_start].destcritid.index(cp_to_remove)
                        df3.loc[cp_start].destcritid[idx] = cp_end
                        df3.loc[cp_start].fillId[idx] = filament_to_grow

                        df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)

                        # Update connectivity of the removed critical point
                        df0.at[cp_to_remove, 'nfil']  = 0


            print(f"{len(rm_fil_idx)} filaments were removed.")
            
            if len(rm_fil_idx) == prev_remaining:
                break



    else:  # 2D skeleton

        # while loop to repeatedly remove short filaments
        while (df2.groupby("filament").size() < threshold_npoints).any():
            prev_remaining = len(rm_fil_idx)
            rm_fil_idx = []

            # Iteratively remove filaments from smallest to largest
            for threshold in np.arange(1, threshold_npoints+1):

                # filaments = df2.filament.unique()
                filaments = df2.groupby("filament").size()[lambda x: x <= threshold].index
        
                # Iterate over each exisiting filament

                for i in filaments:

                    # if len(df2.query(f"filament=={i}").x.values) <= threshold:
                    
                    rm_fil_idx.append(i)

                    cp1, cp2 = df1.query(f"f_id == {i}").cp1.values[0], df1.query(f"f_id == {i}").cp2.values[0]
                    # print("cp1 and cp2: ", cp1, cp2)
                    connection_type = [len(df3.loc[cp1].destcritid),len(df3.loc[cp2].destcritid)]
                    # print ("filament index: ", i, "connection type: ", connection_type)

                    if connection_type != [len(np.unique(df3.loc[cp1].destcritid)),len(np.unique(df3.loc[cp2].destcritid))]:  # Pass over breaking down of loops
                        continue
            
                    if 1 in connection_type and 2 not in connection_type: # Remove the 1-connected CP
                        
                        # Find index of 1-connected CP and other connected CP
                        cp_1_connect, cp_other = [cp1, cp2] if connection_type[0] == 1 else [cp2, cp1]  

                        # Remove 1-connected CP from critical points info
                        df3 = df3.drop(df3.query(f"cp_idx == {cp_1_connect}").index) 

                        # Update the CP and filament conections of the other CP
                        df3.loc[cp_other].destcritid.remove(cp_1_connect) 
                        df3.loc[cp_other].fillId.remove(i)

                        # Remove the short filament from the filament info
                        df1 = df1.drop(df1.query(f"f_id == {i}").index)  

                        # Remove sampling points for filament i 
                        df2 = df2.drop(df2.query(f"filament == {i}").index)  

                        if connection_type == [1,1]:
                            # Remove the other 1-connected CP from critical points info
                            df3 = df3.drop(df3.query(f"cp_idx == {cp_other}").index)
                            # Set the connections of the other CP to zero.
                            df0.at[cp_other, 'nfil'] = 0
                        else:
                            # Decrease the connections of the other CP
                            df0.at[cp_other, 'nfil'] = df0.at[cp_other, 'nfil'] - 1 
                        

                    if all(v >= 3 for v in connection_type):
                        
                        # Determine whcih CP to remove and which to merge into based on their field value
                        cp_to_merge, cp_to_remove = [cp1, cp2] if df0.loc[cp1].field_value > df0.loc[cp2].field_value else [cp2, cp1]

                        # Find all filaments connected to cp_to_remove to grow, besides the filament to be removed
                        filament_to_grow = df3.loc[cp_to_remove].fillId
                        filament_to_grow.remove(i)
                    
                        # Sampling points to grow the filaments by
                        x, y, field = [df2.query(f"filament == {i}").x.values.tolist(), df2.query(f"filament == {i}").y.values.tolist(), df2.query(f"filament == {i}").field_value.values.tolist()]

                        sampling_info = []
                        cp_starts = []

                        for fil in filament_to_grow:
                            for ii in range (len(x)):
                                sampling_info.append([fil, x[ii], y[ii], field[ii]])

                            # Update the endpoint of the merged filament and record the cp of the start of the filaments
                            if df1.loc[fil].cp1 == cp_to_remove:
                                df1.loc[fil].cp1 = cp_to_merge
                                cp_starts.append(df1.loc[fil].cp2)
                            else:
                                df1.loc[fil].cp2 = cp_to_merge
                                cp_starts.append(df1.loc[fil].cp1)
                            
                            # Update the length of the grown filaments
                            df1.at[fil,"nsamp"] = df1.at[fil,"nsamp"] + len(x) 

                        # Update the sampling points associated to the grown filaments
                        df22 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y', 'field_value'], dtype = float).astype({"filament":int, "field_value":int})
                        df2 = pd.concat([df2,df22], ignore_index=True)  # *reset index of rows after concatenating to prevent multiple rows with the same index

                        # Remove the original short filament
                        df2 = df2.drop(df2.query(f"filament == {i}").index)
                        df1 = df1.drop(df1.query(f"f_id == {i}").index)
                        
                        # Remove the cp_to remove
                        df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)

                        # Update the endpoints of the grown filaments
                        df3.loc[cp_to_merge].destcritid.remove(cp_to_remove)
                        df3.loc[cp_to_merge].fillId.remove(i)

                        for c, cp in enumerate(cp_starts):
                            id = df3.loc[cp].destcritid.index(cp_to_remove)
                            df3.loc[cp].destcritid[id] = cp_to_merge
                            df3.at[cp_to_merge, 'destcritid'].append(cp)
                            df3.at[cp_to_merge, 'fillId'].append(filament_to_grow[c])

                        # Update connectivity of the merged critical point, and removed cp
                        df0.at[cp_to_merge, 'nfil'] = df0.at[cp_to_merge, 'nfil'] + len(cp_starts) - 1
                        df0.at[cp_to_remove, 'nfil']  = 0
                    
                    if 2 in connection_type:

                        if any(v >= 3 for v in connection_type): # Merge the short filament by the 2-connected CP
                            cp_2_connect, cp_other = [cp1, cp2] if connection_type[0] == 2 else [cp2, cp1]
                            cp_end = cp_other
                            cp_to_remove = cp_2_connect
                            filament_to_grow = [f for f in df3.query(f"cp_idx == {cp_to_remove}").fillId.values[0] if f!=i][0]
                            cp_start = [c for c in df3.at[cp_to_remove,"destcritid"] if c!= cp_end][0]

                        if connection_type == [2,2]:
                            cp_start = [c for c in df3.at[cp1,"destcritid"] if c!= cp2][0]
                            cp_end = [c for c in df3.at[cp2,"destcritid"] if c!= cp1][0]

                            angle = []

                            # Check which neighbouring filament shares the closest orientation with the short filament
                            for pair in [[cp_start,cp1],[cp1,cp2], [cp2,cp_end]]:
                                cp1_coord, cp2_coord = [df0.loc[pair[0], ['x','y']], df0.loc[pair[1], ['x','y']]]
                                vector = (cp2_coord-cp1_coord).tolist()
                                polar_angle = math.atan2(vector[1],vector[0])
                                angle.append(polar_angle)
        
                            if abs(angle[1]-angle[0]) < abs(angle[2]-angle[1]):
                                cp_to_remove = cp1
                                cp_end = cp2
                                filament_to_grow = [c for c in df3.at[cp1,"fillId"] if c!= i][0]
                            else:
                                cp_to_remove = cp2
                                cp_start = cp_end
                                cp_end = cp1
                                filament_to_grow = [c for c in df3.at[cp2,"fillId"] if c!= i][0]
                            

                        if sorted(connection_type) == sorted([1,2]):
                            cp_1_connect, cp_2_connect = [cp1, cp2] if connection_type[0] == 1 else [cp2, cp1]
                            cp_end = cp_1_connect
                            cp_to_remove= cp_2_connect
                            cp_start = [c for c in df3.at[cp_to_remove,"destcritid"] if c!= cp_end][0]

                            filament_to_grow = [c for c in df3.at[cp_to_remove,"fillId"] if c!= i][0]


                        x, y, field = [df2.query(f"filament == {i}").x.values.tolist(), df2.query(f"filament == {i}").y.values.tolist(), df2.query(f"filament == {i}").field_value.values.tolist()]
                        sampling_info = []

                        # Grow the neighbouring filament by the short filament points
                        for ii in range (len(x)):
                            sampling_info.append([filament_to_grow, x[ii], y[ii], field[ii]])

                        df22 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y', 'field_value'], dtype = float).astype({"filament":int, "field_value":int})
                        df2 = pd.concat([df2,df22], ignore_index=True)  # *reset index of rows after concatenating to prevent multiple rows with the same index
                        
                        # Remove the original short filament
                        df2 = df2.drop(df2.query(f"filament == {i}").index)
                        df1 = df1.drop(df1.query(f"f_id == {i}").index)
                        
                        # Change endpoint of filament to grow
                        if df1.loc[filament_to_grow].cp1 == cp_to_remove:
                            df1.at[filament_to_grow,"cp1"] = cp_end
                        else:
                            df1.at[filament_to_grow,"cp2"] = cp_end   
                        
                        # Update the length of the merged filament
                        df1.at[filament_to_grow,"nsamp"] = df1.at[filament_to_grow,"nsamp"] + len(x)

                        # Update the endpints, filaments of cp_start and cp_end
                        df3.at[cp_end, "destcritid"].remove(cp_to_remove)
                        df3.at[cp_end, "fillId"].remove(i)
                        df3.at[cp_end, "fillId"].append(filament_to_grow)
                        df3.at[cp_end, "destcritid"].append(cp_start)

                        idx = df3.loc[cp_start].destcritid.index(cp_to_remove)
                        df3.loc[cp_start].destcritid[idx] = cp_end
                        df3.loc[cp_start].fillId[idx] = filament_to_grow

                        df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)

                        # Update connectivity of the removed critical point
                        df0.at[cp_to_remove, 'nfil']  = 0

            print(f"{len(rm_fil_idx)} filaments were removed.")

            if len(rm_fil_idx) == prev_remaining:
                break

    skeleton_refined = (df0,df1,df2,df3)

    return skeleton_refined


def join_straight_filaments(skeleton, threshold_angle = np.pi/18):

    df0 = skeleton[0]
    df1 = skeleton[1]
    df2 = skeleton[2]
    df3 = skeleton[3]

    rm_fil_idx = []
    rm_fil_prev = 1 # any random number
    loop = 0

    while rm_fil_prev != len(rm_fil_idx):

        rm_fil_prev = len(rm_fil_idx) # update the number of filaments removed
        endpoint_cps_idx = pd.concat([df1["cp1"], df1["cp2"]]).unique()


        if "z" in df0.columns:

            for cp_to_remove in df0.query("nfil == 2").index.tolist():


                filament_1, filament_2 = df3.loc[cp_to_remove, "fillId"]
                cp_start, cp_end = df3.loc[cp_to_remove, "destcritid"]

                vectors = []

                # Check if neighbouring filament have an orientation within 10 degrees of each other:
                for pair in [[cp_start,cp_to_remove],[cp_to_remove,cp_end]]:
                    cp1_coord, cp2_coord = [df0.loc[pair[0], ['x','y', 'z']], df0.loc[pair[1], ['x','y','z']]]
                    vector = cp2_coord - cp1_coord
                    vectors.append(vector)

                if angle_between_vectors(vectors[1], vectors[0]) <=  threshold_angle:

                    filament_to_grow, filament_to_remove, cp_start, cp_end = [filament_1, filament_2, cp_start, cp_end] if df1.loc[filament_1, "nsamp"] >= df1.loc[filament_2, "nsamp"] else [filament_2, filament_1, cp_end, cp_start]

                    rm_fil_idx.append(filament_to_remove)

                    x, y, z, field = [df2.query(f"filament == {filament_to_remove}").x.values.tolist(), df2.query(f"filament == {filament_to_remove}").y.values.tolist(), df2.query(f"filament == {filament_to_remove}").z.values.tolist(), df2.query(f"filament == {filament_to_remove}").field_value.values.tolist()]
                    
                    sampling_info = []

                    # Grow the neighbouring filament by the short filament points
                    for ii in range (len(x)):
                        sampling_info.append([filament_to_grow, x[ii], y[ii], z[ii], field[ii]])

                    df22 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y', 'z', 'field_value'], dtype = float).astype({"filament":int, "field_value":int})
                    df2 = pd.concat([df2,df22], ignore_index=True)  # *reset index of rows after concatenating to prevent multiple rows with the same index
                    
                    # Remove the original short filament
                    df2 = df2.drop(df2.query(f"filament == {filament_to_remove}").index)
                    df1 = df1.drop(df1.query(f"f_id == {filament_to_remove}").index)
                    
                    # Change endpoint of filament to grow
                    if df1.loc[filament_to_grow].cp1 == cp_to_remove:
                        df1.at[filament_to_grow,"cp1"] = cp_end
                    else:
                        df1.at[filament_to_grow,"cp2"] = cp_end   
                    
                    # Update the length of the merged filament
                    df1.at[filament_to_grow,"nsamp"] = df1.at[filament_to_grow,"nsamp"] + len(x)

                    # Update the endpints, filaments of cp_start and cp_end
                    df3.at[cp_end, "destcritid"].remove(cp_to_remove)
                    df3.at[cp_end, "fillId"].remove(filament_to_remove)
                    df3.at[cp_end, "fillId"].append(filament_to_grow)
                    df3.at[cp_end, "destcritid"].append(cp_start)

                    idx = df3.loc[cp_start].destcritid.index(cp_to_remove)
                    df3.loc[cp_start].destcritid[idx] = cp_end
                    df3.loc[cp_start].fillId[idx] = filament_to_grow

                    df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)

                    # Update connectivity of the removed critical point
                    df0.at[cp_to_remove, 'nfil']  = 0

                else:
                    continue
        else:

            for cp_to_remove in df0.query("nfil == 2").index.tolist():

                filament_1, filament_2 = df3.loc[cp_to_remove, "fillId"]
                cp_start, cp_end = df3.loc[cp_to_remove, "destcritid"]

                vectors = []

                # Check if neighbouring filament have an orientation within 10 degrees of each other:
                for pair in [[cp_start,cp_to_remove],[cp_to_remove,cp_end]]:
                    cp1_coord, cp2_coord = [df0.loc[pair[0], ['x','y']], df0.loc[pair[1], ['x','y']]]
                    vector = cp2_coord - cp1_coord
                    vectors.append(vector)

                if angle_between_vectors(vectors[1], vectors[0]) <= threshold_angle:

                    filament_to_grow, filament_to_remove, cp_start, cp_end = [filament_1, filament_2, cp_start, cp_end] if df1.loc[filament_1, "nsamp"] >= df1.loc[filament_2, "nsamp"] else [filament_2, filament_1, cp_end, cp_start]
                    rm_fil_idx.append(filament_to_remove)

                    x, y, field = [df2.query(f"filament == {filament_to_remove}").x.values.tolist(), df2.query(f"filament == {filament_to_remove}").y.values.tolist(), df2.query(f"filament == {filament_to_remove}").field_value.values.tolist()]
                    
                    sampling_info = []

                    # Grow the neighbouring filament by the short filament points
                    for ii in range (len(x)):
                        sampling_info.append([filament_to_grow, x[ii], y[ii], field[ii]])

                    df22 = pd.DataFrame(sampling_info, columns =['filament', 'x', 'y', 'field_value'], dtype = float).astype({"filament":int, "field_value":int})
                    df2 = pd.concat([df2,df22], ignore_index=True)  # *reset index of rows after concatenating to prevent multiple rows with the same index
                    
                    # Remove the original short filament
                    df2 = df2.drop(df2.query(f"filament == {filament_to_remove}").index)
                    df1 = df1.drop(df1.query(f"f_id == {filament_to_remove}").index)
                    
                    # Change endpoint of filament to grow
                    if df1.loc[filament_to_grow].cp1 == cp_to_remove:
                        df1.at[filament_to_grow,"cp1"] = cp_end
                    else:
                        df1.at[filament_to_grow,"cp2"] = cp_end   
                    
                    # Update the length of the merged filament
                    df1.at[filament_to_grow,"nsamp"] = df1.at[filament_to_grow,"nsamp"] + len(x)

                    # Update the endpints, filaments of cp_start and cp_end
                    df3.at[cp_end, "destcritid"].remove(cp_to_remove)

                    df3.at[cp_end, "fillId"].remove(filament_to_remove)
                    df3.at[cp_end, "fillId"].append(filament_to_grow)

                    df3.at[cp_end, "destcritid"].append(cp_start)

                    idx = df3.loc[cp_start].destcritid.index(cp_to_remove)
                    df3.loc[cp_start].destcritid[idx] = cp_end
                    df3.loc[cp_start].fillId[idx] = filament_to_grow

                    df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)

                    # Update connectivity of the removed critical point
                    df0.at[cp_to_remove, 'nfil']  = 0

                else:
                    continue
        
        loop+=1

    print(f"{len(rm_fil_idx)} filaments were removed.")
    skeleton_refined = (df0,df1,df2,df3)

    return skeleton_refined 


def flatten(iterable):
        for item in iterable:
            if isinstance(item, (list, tuple, set)):
                return flatten(item)
            else:
                return item 
                        

def remove_dangling_ends(skeleton):
  
    # This function removes any dangling ends, which are filaments that have a one-connection. 
    # These can be by themseleves ("broken filament" from the network) or attached only on one end to the percolating network structure.

    df0 = skeleton[0]
    df1 = skeleton[1]
    df2 = skeleton[2]
    df3 = skeleton[3]

    past_cps = []
    past_filaments = [] 
    filaments_removed = 0

    while len(df0.query("nfil == 1").index.tolist()) != 0 : # 2-connections can turn into 1-connections after one round of removing, so we continuously loop until no 1-connections remain.
            
        for cp_to_remove in df0.query("nfil == 1").index.tolist():

            # print("cp to remove: ", cp_to_remove)

            assert (len(df3.query(f"cp_idx =={cp_to_remove}").destcritid) == 1 )
            assert (len(df3.query(f"cp_idx =={cp_to_remove}").fillId) == 1 )

            if cp_to_remove in past_cps:  # This means that both cps were conencted by only one filament, aka. broken filaments

                # Change the number of filaments attached to the critical points cp_to_remove, the original filament and its connected cp should have already been previously removed
                df0.at[cp_to_remove, 'nfil'] = 0
                df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)
                
                continue

            cp2 = flatten(df3.query(f"cp_idx =={cp_to_remove}").destcritid.tolist())
            filament_to_remove = flatten(df3.query(f"cp_idx =={cp_to_remove}").fillId.tolist())

            # Change the number of filaments attached to the critical points cp_to_remove and cp2
            df0.at[cp_to_remove, 'nfil'] = 0
            df0.at[cp2, 'nfil'] = df0.at[cp2, 'nfil'] - 1 

            # Remove the index of the original filament 
            df1 = df1.drop(df1.query(f"f_id == {filament_to_remove}").index)

            # Remove all sampling points of the original filament 
            df2 = df2.drop(df2.query(f"filament == {filament_to_remove}").index)
            
            # Update the endpoints of cp2
            df3.query(f"cp_idx =={cp2}").destcritid.tolist()[0].remove(cp_to_remove)
            df3.query(f"cp_idx =={cp2}").fillId.tolist()[0].remove(filament_to_remove)
            df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)
            
            past_cps.append(cp_to_remove)

            if df0.at[cp2, 'nfil'] == 0:
                past_cps.append(cp2)
                df3.drop(df3.query(f"cp_idx == {cp2}").index)

            filaments_removed += 1

    skeleton_refined = (df0,df1,df2,df3)

    print(f"{filaments_removed} filaments were removed.")

    return skeleton_refined


def remove_broken_ends(skeleton):
    
    df0 = skeleton[0]
    df1 = skeleton[1]
    df2 = skeleton[2]
    df3 = skeleton[3]

    past_filaments = []
    broken_filaments = []

    for cp_to_remove in df0.query("nfil == 1").index.tolist():

        cp2 = flatten(df3.query(f"cp_idx =={cp_to_remove}").destcritid.tolist())
        filament_to_remove = flatten(df3.query(f"cp_idx =={cp_to_remove}").fillId.tolist())

        if cp2 == None:
            df0.at[cp_to_remove, 'nfil'] = 0
            continue

        if df0.at[cp2, 'nfil'] == 1:
            if filament_to_remove in past_filaments:
                continue
            past_filaments.append(filament_to_remove)
            broken_filaments.append([cp_to_remove, cp2, filament_to_remove])
        

    for cp1, cp2, filament_to_remove in broken_filaments:
        
        # Change the number of filaments attached to the critical points cp1 and cp2
        df0.at[cp1, 'nfil'] = 0
        df0.at[cp2, 'nfil'] = 0

        # Remove the index of the original filament 
        df1 = df1.drop(df1.query(f"f_id == {filament_to_remove}").index)
        
        # Remove all sampling points of the original filament 
        df2 = df2.drop(df2.query(f"filament == {filament_to_remove}").index)

        # Update the endpoints of cp2

        df3 = df3.drop(df3.query(f"cp_idx == {cp1}").index)
        df3 = df3.drop(df3.query(f"cp_idx == {cp2}").index)

    skeleton_refined = (df0,df1,df2,df3)

    print(f"{len(broken_filaments)} filaments were removed.")

    return skeleton_refined

def remove_spurious_ends(skeleton, threshold_points = 7):
    
    df0 = skeleton[0]
    df1 = skeleton[1]
    df2 = skeleton[2]
    df3 = skeleton[3]

    past_filaments = []
    spurious_filaments = []

    for cp_to_remove in df0.query("nfil == 1").index.tolist():

        cp2 = flatten(df3.query(f"cp_idx =={cp_to_remove}").destcritid.tolist())
        filament_to_remove = flatten(df3.query(f"cp_idx =={cp_to_remove}").fillId.tolist())

        if cp2 == None:
            df0.at[cp_to_remove, 'nfil'] = 0
            continue

        if df0.at[cp2, 'nfil'] in [2,3,4,5] and len(df2.query(f"filament == {filament_to_remove}").x.tolist()) < threshold_points:

            if filament_to_remove in past_filaments:
                continue
            past_filaments.append(filament_to_remove)
            spurious_filaments.append([cp_to_remove, cp2, filament_to_remove])
        

    for cp1, cp2, filament_to_remove in spurious_filaments:

        cp_to_remove, cp_to_keep = [cp1, cp2] if df0.at[cp1, 'nfil'] < df0.at[cp2, 'nfil'] else [cp2, cp1]

        # Change the number of filaments attached to the critical points cp1 and cp2
        df0.at[cp_to_remove, 'nfil'] = 0
        df0.at[cp_to_keep, 'nfil'] = df0.at[cp_to_keep, 'nfil'] - 1

        # Remove the index of the original filament 
        df1 = df1.drop(df1.query(f"f_id == {filament_to_remove}").index)
        
        # Remove all sampling points of the original filament 
        df2 = df2.drop(df2.query(f"filament == {filament_to_remove}").index)

        # Update the endpoints of cp2
        df3 = df3.drop(df3.query(f"cp_idx == {cp_to_remove}").index)
        df3.query(f"cp_idx =={cp_to_keep}").destcritid.tolist()[0].remove(cp_to_remove)
        df3.query(f"cp_idx =={cp_to_keep}").fillId.tolist()[0].remove(filament_to_remove)
            

    skeleton_refined = (df0,df1,df2,df3)

    print(f"{len(spurious_filaments)} filaments were removed.")

    return skeleton_refined

def angle_between_vectors(vec1, vec2):

    dot_product = np.dot(vec1, vec2)
    norm_vector1 = np.linalg.norm(vec1)
    norm_vector2 = np.linalg.norm(vec2)
    
    cos_theta = dot_product / (norm_vector1 * norm_vector2)

    if norm_vector1 * norm_vector2 == 0:
        cos_theta = dot_product / (1e-21)

    angle_rad = np.arccos(cos_theta)

    if angle_rad > np.pi/2:
        angle_rad = np.pi - angle_rad
    
    return angle_rad

def threshold_number_points(skeleton, pixel_size, threshold_length):

    sampling_points = skeleton[2].query(f"filament=={1}")[["x","y"]].multiply({"x": pixel_size[0], 'y': pixel_size[0]}).values

    if "z" in skeleton[0].columns:
        sampling_points = skeleton[2].query(f"filament=={1}")[["x","y", "z"]].multiply({"x": pixel_size[1], 'y': pixel_size[1], "z": pixel_size[0]}).values
    
    sampling_points_density = np.mean(np.linalg.norm(sampling_points[1:] - sampling_points[:-1], axis=1), axis=0)  # Average distance between sampling points (um)
    sampling_threshold = int(threshold_length /sampling_points_density)  # number of pixels corresponding to length of 1 um

    return sampling_threshold

class SkeletonObject:

    def __init__(self, raw_skeleton, pixel_size):

        self.skeleton = raw_skeleton
        self.pixel_size = pixel_size  # [size of pixel in z and in xy] in um    

    def skeleton_processing(self, angle_threshold = np.pi/18, length_threshold = 1):

        threshold_points = threshold_number_points(self.skeleton, self.pixel_size, length_threshold)

        self.skeleton = filament_breakdown_node_correction(self.skeleton)

        self.skeleton = clean_short_filaments(self.skeleton, threshold_points)

        self.skeleton = join_straight_filaments(self.skeleton, angle_threshold)

        return self
    
    def dangling_ends(self):

        self.skeleton = remove_dangling_ends(self.skeleton)

        return self

    def broken_ends(self):

        self.skeleton = remove_broken_ends(self.skeleton)

        return self
    
    def spurious_ends(self):

        self.skeleton = remove_spurious_ends(self.skeleton)

        return self
    
    def short_filaments(self, length_threshold = 1):

        threshold_points = threshold_number_points(self.skeleton, self.pixel_size, length_threshold)

        self.skeleton = clean_short_filaments(self.skeleton, threshold_points)

        return self

    
    def assemble_filaments(self, angle_threshold = np.pi/18):

        self.skeleton = join_straight_filaments(self.skeleton, angle_threshold)

        return self

    
    def save_skeleton(self, filename):

        with open(filename+".pkl", 'wb') as f:
            pickle.dump(self.skeleton, f)

        print("The skeleton has been saved to " + filename + ".pkl")

        return self
    
def load_skeleton(filename):

    with open(filename, 'rb') as f:
        skeleton =  pickle.load(f)

    print("The skeleton has been loaded.")

    return skeleton
