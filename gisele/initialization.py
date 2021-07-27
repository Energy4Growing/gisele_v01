"""
GIS For Electrification (GISEle)
Developed by the Energy Department of Politecnico di Milano
Initialization Code

Code for importing input GIS files, perform the weighting strategy and creating
the initial Point geodataframe.
"""

import os
import math
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from gisele.functions import l, s
import osmnx as ox


def roads_import(geo_df,crs):
    '''
    Download road layers from OpenStreetMaps, and simplify geometries to use
    them for the grid routing algorithms
    :param df:
    :return:
    '''
    geo_df.to_crs(epsg=4326,inplace=True)
    bounds = geo_df.geometry.total_bounds
    print('Downloading roads, from OpenStreetMap..')
    graph = ox.graph_from_bbox(bounds[1], bounds[3],
                               bounds[0], bounds[2], network_type='drive_service')
    ox.save_graph_shapefile(graph,
                            filepath='Output/Datasets/Roads')  # crs is 4326
    #simplify geometry
    roads = gpd.read_file('Output/Datasets/Roads/edges.shp')
    roads_simple = roads.geometry.simplify(tolerance=0.0005)
    roads_simple = roads_simple.to_crs(epsg=int(crs))
    roads_simple.to_file('Output/Datasets/Roads/roads.shp')


def weighting(df, resolution, landcover_option):
    """
    Assign weights to all points of a dataframe according to the terrain
    characteristics and the distance to the nearest road.
    :param df: From which part of GISEle the user is starting
    :param resolution: resolution of the dataframe df
    :return df_weighted: Point dataframe with weight attributes assigned
    """
    df_weighted = df.dropna(subset=['Elevation'])
    df_weighted.reset_index(drop=True)
    df_weighted.Slope.fillna(value=0, inplace=True)
    df_weighted.Land_cover.fillna(method='bfill', inplace=True)
    df_weighted['Land_cover'] = df_weighted['Land_cover'].round(0)
    df_weighted.Population.fillna(value=0, inplace=True)
    df_weighted['Weight'] = 0
    print('Weighting the Dataframe..')
    os.chdir(r'Input//')
    landcover_csv = pd.read_csv('Landcover.csv')
    os.chdir(r'..//')
    del df
    # Weighting section
    # Slope conditions
    df_weighted['Weight'] = math.e**(
        0.01732867951 * df_weighted['Slope'])
    # Land cover using the column Other or GLC to compute the weight
    for i,row in landcover_csv.iterrows():
        if landcover_option == 'GLC':
            df_weighted.loc[
                df_weighted['Land_cover'] == row['GLC2000'], 'Weight'] += \
            landcover_csv.loc[i, 'WeightGLC']
        else:
            df_weighted.loc[
                df_weighted['Land_cover'] == row['Other'], 'Weight'] += \
            landcover_csv.loc[i, 'WeightOther']
    # Road distance conditions
    df_weighted.loc[df_weighted['Road_dist'] < 1000, 'Weight'] += \
        5 * df_weighted.loc[
                  df_weighted[
                      'Road_dist'] < 1000, 'Road_dist'] / 1000

    df_weighted.loc[df_weighted['Road_dist'] >= 1000,'Weight'] += 5
    df_weighted.loc[df_weighted['Road_dist'] < resolution / 2, 'Weight'] = 1.5
    #Protected areas condition
    df_weighted.loc[df_weighted['Protected_area'] == True, 'Weight'] += 5

    valid_fields = ['ID', 'X', 'Y', 'Population', 'Elevation', 'Weight']
    blacklist = []
    for x in df_weighted.columns:
        if x not in valid_fields:
            blacklist.append(x)
    df_weighted.drop(blacklist, axis=1, inplace=True)
    df_weighted.drop_duplicates(['ID'], keep='last', inplace=True)
    print("Cleaning and weighting process completed")
    s()
    return df_weighted


def creating_geodataframe(df_weighted, crs, unit, input_csv, step):
    """
    Based on the input weighted dataframe, creates a geodataframe assigning to
    it the Coordinate Reference System and a Point geometry
    :param df_weighted: Input Point dataframe with weight attributes assigned
    :param crs: Coordinate Reference System of the electrification project
    :param unit: Type of CRS unit used if degree or meters
    :param input_csv: Name of the input file for exporting the geodataframe
    :param step: From which part of GISEle the user is starting
    :return geo_df: Point geodataframe with weight, crs and geometry defined
    :return pop_points: Dataframe containing only the coordinates of the points
    """
    print("Creating the GeoDataFrame..")
    geometry = [Point(xy) for xy in zip(df_weighted['X'], df_weighted['Y'])]
    geo_df = gpd.GeoDataFrame(df_weighted, geometry=geometry,
                              crs=int(crs))

    # - Check crs conformity for the clustering procedure
    if unit == '0':
        print('Attention: the clustering procedure requires measurements in '
              'meters. Therefore, your dataset must be reprojected.')
        crs = int(input("Provide a valid crs code to which reproject:"))
        geo_df['geometry'] = geo_df['geometry'].to_crs(epsg=crs)
        print("Done")
    print("GeoDataFrame ready!")
    s()
    if step == 1:
        #os.chdir(r'Output//Datasets')
        geo_df.to_csv('Output/Datasets/'+input_csv + "_weighted.csv")
        geo_df.to_file('Output/Datasets/'+input_csv + "_weighted.shp")
        #os.chdir(r'..//..')
        print("GeoDataFrame exported. You can find it in the output folder.")
        l()

    print("In the considered area there are " + str(
        len(geo_df)) + " points, for a total of " +
          str(int(geo_df['Population'].sum(axis=0))) +
          " people which could gain access to electricity.")

    loc = {'x': geo_df['X'], 'y': geo_df['Y'], 'z': geo_df['Elevation']}
    pop_points = pd.DataFrame(data=loc).values

    return geo_df, pop_points
