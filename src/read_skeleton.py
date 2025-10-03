import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _readline(f):
    '''
    Function from Merle et. al. (2023), doi: 10.1016/J.DEVCEL.2023.07.017
    '''
    for line in f:
        # Skip comment line
        if line.find('#') != 0:
            break
    return line


def _check_pattern(line, pattern, optionnal=False):
    '''
    Function from Merle et. al. (2023), doi: 10.1016/J.DEVCEL.2023.07.017
    '''
    if line.find(pattern) != 0:
        if not(optionnal):
            raise ValueError('Wrong format, missing {}'.format(pattern))
    else:
        return line


def load_NDskl(filename):
    """ Read NDskl file and generate two dataframe which
    contains critical point and filament
    
    Function from Merle et. al. (2023), doi: 10.1016/J.DEVCEL.2023.07.017

    Parameters
    ----------
    filename: str, Path to the file

    Returns
    -------
    cp_df : pd.DataFrame
    fil_df : pd.DataFrame
    fil_point : pd.DataFrame
    specs : Dict
    cp_filament_info : Dict

    """
    specs = {}

    with open(filename, 'r') as f:

        # 2D or 3D images
        if _check_pattern(_readline(f), 'ANDSKEL'):
            specs['ndims'] = int(_readline(f))

        # Size of the image
        line = _check_pattern(_readline(f), 'BBOX', optionnal=True)
        if line:
            bbox, bbox_delta = re.findall('\[.*?\]', line)
            specs['bbox'] = np.asfarray(bbox[1:-1].split(','))
            specs['bbox_delta'] = np.asfarray(bbox_delta[1:-1].split(','))

        # CRITICAL POINTS
        cp_filament_info = {}
        if _check_pattern(_readline(f), '[CRITICAL POINTS]'):
            specs['ncrit'] = int(_readline(f))

            # Bloc of informations for each critical point
            # l1 : type pos, val, pair, boundary
            # l2 : number of filament connected to the CP
            # l3-l_num_fil : filament information
            datas = {}
            for i in range(specs['ncrit']):
                data = {}
                # l1
                line1 = _readline(f).split()
                data['type'] = int(line1[0])

                for n in range(specs['ndims']):
                    data[list('xyz')[n]] = float(line1[1 + n])

                data['val'] = float(line1[1 + specs['ndims']])
                data['pair'] = float(line1[2 + specs['ndims']])
                data['boundary'] = float(line1[3 + specs['ndims']])
                # l2
                data['nfil'] = int(_readline(f))
                # l3-l_num_fil
                cp_filament_info[i] = {'destcritid': [None] * data['nfil'],
                                           'fillId': [None] * data['nfil']}
                for j in range(data['nfil']):
                    line = _readline(f).split()
                    #cp_filament_info[i] = {'destcritid': int(line[0]),
                    #                       'fillId': int(line[1])}
                    cp_filament_info[i]['destcritid'][j] = int(line[0])
                    cp_filament_info[i]['fillId'][j] = int(line[1])
                # Put information in DataFrame
                datas[i] = data
            cp_df = pd.DataFrame.from_dict(datas, orient='index')

        # FILAMENTS
        fils = {}
        cpt_fils = 0
        if _check_pattern(_readline(f), '[FILAMENTS]'):
            specs['nfil'] = int(_readline(f))

            # Bloc of informations for each filament
            # l1 : cp1, cp2, nsamp
            # l2-l... : points informations of filament
            datas = {}
            for i in range(specs['nfil']):
                data = {}
                # l1
                line1 = _readline(f).split()
                data['cp1'] = int(line1[0])
                data['cp2'] = int(line1[1])
                data['nsamp'] = int(line1[2])
                for _ in range(data['nsamp']):
                    line = _readline(f).split()
                    fil = {}
                    for n in range(specs['ndims']):
                        fil[list('xyz')[n]] = float(line[n])
                        fil['filament'] = i

                    fils[cpt_fils] = fil
                    cpt_fils += 1

                datas[i] = data
            # Put information in DataFrame
            fil_df = pd.DataFrame.from_dict(datas, orient='index')
            fil_points = pd.DataFrame.from_dict(fils, orient='index')

        # CRITICAL POINT supplementary information
        if _check_pattern(_readline(f), '[CRITICAL POINTS DATA]', optionnal=True):
            ninfo = int(_readline(f))
            crit_columns_name = []
            for i in range(ninfo):
                crit_columns_name.append(_readline(f)[:-1])

            datas = {}
            for i in range(specs['ncrit']):
                data = {}
                line = _readline(f).split()
                for ii in range(ninfo):
                    data[crit_columns_name[ii]] = line[ii]
                datas[i] = data
            cp_supp = pd.DataFrame.from_dict(datas, orient='index')
        # merge cp_df and cp_supp
        cp_df = pd.concat([cp_df, cp_supp], axis=1, sort=False)

        # FILAMENT supplementary information
        if _check_pattern(_readline(f), '[FILAMENTS DATA]', optionnal=True):
            ninfo = int(_readline(f))
            fil_columns_name = []
            for i in range(ninfo):
                fil_columns_name.append(_readline(f)[:-1])

            datas = {}
            for i in range(fil_points.shape[0]):
                data = {}
                line = _readline(f).split()
                for ii in range(ninfo):
                    data[fil_columns_name[ii]] = line[ii]
                datas[i] = data
            fil_supp = pd.DataFrame.from_dict(datas, orient='index')
        # merge cp_df and cp_supp
        fil_points = pd.concat([fil_points, fil_supp], axis=1, sort=False)
        
    cp_filinfo_df = pd.DataFrame(data={'destcritid': [cp_filament_info[i]['destcritid']
                                                 for i in range(len(cp_filament_info))],
                             'fillId': [cp_filament_info[i]['fillId']
                                                 for i in range(len(cp_filament_info))]})

    return cp_df, fil_df, fil_points, cp_filinfo_df, specs

