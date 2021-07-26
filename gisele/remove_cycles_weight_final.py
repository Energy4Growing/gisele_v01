# -*- coding: utf-8 -*-
"""
Created on Tue May  7 16:20:43 2019

@author: Silvia
"""
import pandas as pd
import numpy as np
import geopandas as gpd
import networkx as nx


def remove_cycles(grid, gdf, gdf_in):
    # check cycles
    # create empty matrix to be filled with connections of Steiner: adjacency matrix
    
    print('begin Cycle_matrix_creation')
    grid_points = grid['ID1'].values
    grid_points = np.vstack((grid_points, grid['ID2'])).transpose()
    graph = grid_points.tolist()
    H = nx.Graph(graph)
    Adjacency_matrix = nx.adjacency_matrix(H)
    Cycle_matrix = pd.DataFrame(data=Adjacency_matrix.todense())
    Cycle_matrix.index = H.nodes
    Cycle_matrix.columns = H.nodes
    print('end Cycle_matrix_creation') 
#    Cycle_matrix=pd.DataFrame()
#    for i, row in grid.iterrows():
#        print(i)
#        Cycle_matrix.at[row['ID1'],row['ID2']]=1
#        Cycle_matrix.at[row['ID2'],row['ID1']]=1     
    # remove nan values: columns and rows with no connection
    Cycle_matrix = Cycle_matrix.dropna(axis=0, how='all')
    Cycle_matrix = Cycle_matrix.dropna(axis=1, how='all')
    Cycle_matrix['sum'] = Cycle_matrix.sum(axis=1, skipna=True)
    Cycle_matrix['cross_point'] = Cycle_matrix['sum'] > 2
    Cross_points = Cycle_matrix['cross_point']
    Cross_points = Cross_points[Cross_points == True]
    # reorder dataframe columns to make the matrix simmetrical
    indices = list(Cycle_matrix.index)
    Cycle_matrix = Cycle_matrix[indices]
    Cycle_matrix['sum'] = Cycle_matrix.sum(axis=1, skipna=True)
    # Cycle_matrix['pop_point'] = Cycle_matrix_new['pop_point']
    # remove perypheric points (points which have only one connection)
    print('removing peripherical points')
    while any(Cycle_matrix['sum'] < 2):
        # remove rows which sum is equal to 1
        peripheric_point = Cycle_matrix[Cycle_matrix['sum'] < 2].index
        #print(peripheric_point)#
        Cycle_matrix = Cycle_matrix.drop(index=peripheric_point)
        Cycle_matrix = Cycle_matrix.drop(columns=peripheric_point)
        Cycle_matrix = Cycle_matrix.drop(columns=['sum'])
        Cycle_matrix['sum'] = Cycle_matrix.sum(axis=1, skipna=True)
    print('peripheric points removed')
    
    cycle = Cycle_matrix.drop(columns=['sum'])
    indices = list(Cycle_matrix.index)
    cycle = cycle.fillna(0)
    cycle_points = np.transpose(np.nonzero(np.triu(cycle.values)))
    N = cycle.shape[0]
#    graph = cycle_points.tolist()

    cycles = np.empty((N+1, N+1))
    cycles[:] = np.nan
    N = cycle.shape[0]
    Cycle_matrix['sum'] = Cycle_matrix.sum(axis=1, skipna=True)
#    max_intersection = Cycle_matrix['sum'].max()
#    cycle_points1 = cycle_points
    indices = np.asarray(indices)
    j = 0
    count = 0
    grid.index = range(0, len(grid['ID1']))
    grid_without_cycles = grid[:]
    
    for i in range(N):
        cycle_points1 = cycle_points
        x = i
        if (cycles == x).any():
            continue
        k = 0
        while (x != cycles[:, j]).all():
            if (cycles[:, 0:j] == x).any():
                count = count+1
            if count == 2:
                cycles[:, j] = np.nan
                count = 0
                j = j-1
                break
            cycles[k, j] = x
            position_row = np.where(cycle_points1 == x)[0]
            position_row = position_row[0]
            position_column = np.where(cycle_points1 == x)[1]
            position_column = position_column[0]
            if position_column == 0:
                x = cycle_points1[position_row, 1]
            else:
                x = cycle_points1[position_row, 0]
            k = k+1
            cycle_points1 = np.delete(cycle_points1, position_row, 0)
            pos = k
            poss = j
        print('end cycle')
        cycles[pos, poss] = x
        first = np.where(cycles[:, poss] == x)[0]
        first = first[0]
        cycles[0:first, poss] = np.nan
        j = j+1
    # remove rows and columns with only nan values
    cycles = cycles[~np.isnan(cycles).all(axis=1), :]
    cycles = cycles[:, ~np.isnan(cycles).all(axis=0)]
    columns_to_remove = (~np.isnan(cycles)).sum(axis=0)
    columns_to_keep = np.squeeze(np.transpose((np.where(columns_to_remove > 2))))
    cycles = cycles[:, columns_to_keep]
    if len(cycles.shape) == 2:
        ID1 = cycles.shape[1]
    else:
        ID1 = 1
    cycles1 = cycles[:]
    for i in range(ID1):
        if len(cycles.shape) == 2:
            Selection = cycles1[:, i]
        else:
            Selection = cycles1
        Selection = (Selection[~np.isnan(Selection)])
        Selection = Selection.astype(int)
        if Selection[len(Selection)-1] != Selection[0]:
            Selection = np.delete(Selection, (len(Selection)-1), axis=0)
        Selection_id = indices[Selection]
        if len(cycles.shape) == 2:
            cycles1[0:len(Selection_id), i] = Selection_id
        else:
            cycles1[0:len(Selection_id)] = Selection_id
        Selection_id = pd.DataFrame(data=Selection_id)
        Selection_id.columns = ['ID']
        Selection_id['important'] = ""
        Selection_id['X'] = ""
        Selection_id['Y'] = ""
        Selection_id['Weight'] = ""
        Selection_id['Elevation'] = ""
        Selection_id['Distance'] = ""
        Selection_id['Distance_cum'] = ""
        Selection_id['Impo_Distance_cum'] = np.nan
        for k, row in Selection_id.iterrows():
            if (Cross_points.index == row['ID']).any() | (gdf['ID'] == row['ID']).any():
                Selection_id.at[k, ['important']] = 1
            else:
                Selection_id.at[k, ['important']] = 0
            Selection_id.at[k, ['X']] = gdf_in[gdf_in['ID'] == row['ID']]['X'].values
            Selection_id.at[k, ['Y']] = gdf_in[gdf_in['ID'] == row['ID']]['Y'].values
            Selection_id.at[k, ['Weight']] = gdf_in[gdf_in['ID'] == row['ID']]['Weight'].values
            Selection_id.at[k, ['Elevation']] = gdf_in[gdf_in['ID'] == row['ID']]['Elevation'].values
        Selection_id.at[0, ['Distance']] = 0
        for j, row in Selection_id.iterrows():
            if j == 0:
                continue
            # AGGIUNGERE PARTE PER DIFFERENZIARE GRADI DA METRI!!!
            Selection_id.at[j, ['Distance']] = ((row['X'] - Selection_id.loc[j-1, ['X']].values)**2 +
                                                (row['Y'] - Selection_id.loc[j-1, ['Y']].values)**2 +
                                                (row['Elevation'] - Selection_id.loc[j-1, ['Elevation']].values)**2)**0.5
            Selection_id.at[j, ['Distance']] = \
                Selection_id.loc[j, ['Distance']]*(row['Weight'] + Selection_id.loc[j-1, ['Weight']].values)/2
        for w, row in Selection_id.iterrows():
            if w == 0:
                Selection_id.at[w, ['Distance_cum']] = 0
                continue
            if Selection_id.loc[w, ['important']].values == 0:
                Selection_id.at[w, ['Distance_cum']] = \
                    Selection_id.loc[w-1, ['Distance_cum']].values+Selection_id.loc[w, ['Distance']].values
            else:
                Selection_id.at[w, ['Distance_cum']] = 0
                Selection_id.at[w, ['Impo_Distance_cum']] = \
                    Selection_id.loc[w-1, ['Distance_cum']].values+Selection_id.loc[w, ['Distance']].values
        maximum = Selection_id['Impo_Distance_cum'].max()
        important_points = Selection_id[Selection_id['important'] == 1]
        important_points.index = range(0, len(important_points['ID']))
        second_point = important_points[important_points['Impo_Distance_cum'] == maximum]['ID']
        first_point = (important_points.loc[second_point.index-1, ['ID']])
        second_point = int(second_point.values[0])
        first_point = int(first_point.values[0])
        pos_first = int(Selection_id[Selection_id['ID'] == first_point].index.values[0])
        pos_second = Selection_id[Selection_id['ID'] == second_point].index.values
        if len(pos_second) == 2:
            pos_second = int(pos_second[1])
        else:
            pos_second = int(pos_second[0])
        for s in range(pos_first, pos_second):
            first_point1 = int(Selection_id.loc[s, ['ID']].values[0])
            second_point1 = int(Selection_id.loc[s+1, ['ID']].values[0])
            grid_without_cycles = \
                grid_without_cycles.drop(grid_without_cycles[(grid_without_cycles['ID1'] == first_point1) &
                                                             (grid_without_cycles['ID2'] == second_point1)].index)
            grid_without_cycles = \
                grid_without_cycles.drop(grid_without_cycles[(grid_without_cycles['ID2'] == first_point1) &
                                                             (grid_without_cycles['ID1'] == second_point1)].index)
            #print(len(grid_without_cycles['ID1']))#
    # compute distance between one point and the following in the matrix containing cycles
    print('end')
    return grid_without_cycles
