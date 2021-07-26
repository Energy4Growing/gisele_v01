import zipfile
import os
import rasterio.mask
from osgeo import gdal
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from shapely.geometry import Point, MultiPoint, MultiPolygon
from shapely.ops import nearest_points


def create_mesh(study_area, crs, resolution, imported_pop=pd.DataFrame()):

    print('Processing the imported data and creating the input csv file..')
    df = pd.DataFrame(columns=['ID', 'X', 'Y', 'Elevation', 'Slope',
                               'Population', 'Land_cover', 'Road_dist',
                               'River_flow','Protected_area'])

    study_area = study_area.to_crs(crs)
    min_x, min_y, max_x, max_y = study_area.geometry.total_bounds
    # re-project layer according to metric coordinate system
    # create one-dimensional arrays for x and y
    lon = np.arange(min_x, max_x, resolution)
    lat = np.arange(min_y, max_y, resolution)
    lon, lat = np.meshgrid(lon, lat)

    # improvements: add rivers and protected areas
    df['X'] = lon.reshape((np.prod(lon.shape),))
    df['Y'] = lat.reshape((np.prod(lat.shape),))

    if not imported_pop.empty:
        pop_data = pd.read_csv(r'Input/imported_pop.csv')
        valid_fields = ['X', 'Y', 'Population']
        blacklist = []
        for x in pop_data.columns:
            if x not in valid_fields:
                blacklist.append(x)
        pop_data.drop(blacklist, axis=1, inplace=True)
        df = pd.concat([df, pop_data])

    # create geo-data-frame out of df and clip it with the area
    geo_df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.X, df.Y),
                              crs=crs)
    geo_df.reset_index(drop=True, inplace=True)
    geo_df = gpd.clip(geo_df, study_area)
    geo_df.reset_index(drop=True, inplace=True)
    geo_df['ID'] = geo_df.index
    # import vector files
    streets = gpd.read_file('Output/Datasets/Roads/edges.shp')
    # save again vector file with the correct name
    streets.to_file('Output/Datasets/Roads/roads.shp')
    streets = streets.to_crs(crs)
    streets_points = []
    for line in streets['geometry']:
        for x in list(zip(line.xy[0], line.xy[1])):
            streets_points.append(x)
    streets_multipoint = MultiPoint(streets_points)
    if os.path.exists('Output/Datasets/ProtectedAreas/ProtectedAreas.shp'):
        prot_exist=True
        protected_areas = gpd.read_file('Output/Datasets/ProtectedAreas/ProtectedAreas.shp')
        protected_areas = protected_areas.to_crs(crs)
        protected_areas = protected_areas[protected_areas['IUCN_CAT'].isin(['II','I'])]
    else:
        prot_exist=False

    # Manage raster files and sample their values
    # extract zipped files #
    with zipfile.ZipFile('Output/Datasets/Elevation/Elevation.zip', 'r') as zip_ref:
        zip_ref.extractall('Output/Datasets/Elevation')
    with zipfile.ZipFile('Output/Datasets/LandCover/LandCover.zip', 'r') as zip_ref:
        zip_ref.extractall('Output/Datasets/LandCover')
    with zipfile.ZipFile('Output/Datasets/Population/Population.zip', 'r') as zip_ref:
        zip_ref.extractall('Output/Datasets/Population')

    # find the name of the raster files
    file_elevation = os.listdir('Output/Datasets/Elevation')
    file_land_cover = os.listdir('Output/Datasets/LandCover')
    file_population = os.listdir('Output/Datasets/Population')

    # open files with rasterio
    for i in range(file_elevation.__len__()):

        if file_elevation[i].endswith('.tif'):
            raster_elevation = rasterio.open('Output/Datasets/Elevation/'
                                             + file_elevation[i])
            # compute slope
            gdal.DEMProcessing('Output/Datasets/Elevation/slope.tif',
                               'Output/Datasets/Elevation/' + file_elevation[
                                   i],
                               'slope')
            raster_slope = rasterio.open('Output/Datasets/Elevation/slope.tif')

        if file_land_cover[i].endswith('.tif'):
            raster_land_cover = rasterio.open('Output/Datasets/LandCover/'
                                              + file_land_cover[i])
        if file_population[i].endswith('.tif'):
            raster_population = rasterio.open('Output/Datasets/Population/'
                                              + file_population[i])

    # re-sample continuous raster according to the desired resolution(bilinear)

    data_elevation, profile_elevation = resample(raster_elevation, resolution)
    data_slope, profile_slope = resample(raster_slope, resolution)

    # write re-sampled values in a new raster
    with rasterio.open('Output/Datasets/Elevation/elevation_resampled.tif',
                       'w', **profile_elevation) as dst:
        dst.write(data_elevation)
        # dst.write(data_elevation.astype(rasterio.int16))
    with rasterio.open('Output/Datasets/Elevation/slope_resampled.tif', 'w',
                       **profile_slope) as dst:
        dst.write(data_slope)
        # dst.write(data_slope.astype(rasterio.float32))
    # reopen resampled values. It seems stupid, need to check for a faster way
    raster_elevation_resampled = \
        rasterio.open('Output/Datasets/Elevation/elevation_resampled.tif')
    raster_slope_resampled = \
        rasterio.open('Output/Datasets/Elevation/slope_resampled.tif')

    # read arrays of raster layers
    elevation_resampled = raster_elevation_resampled.read()
    slope_resampled = raster_slope_resampled.read()
    land_cover = raster_land_cover.read()
    population = raster_population.read()
    # get population cell size to understand how to sample it
    affine_pop = raster_population.transform
    pixel_x_pop = affine_pop[0]

    # sample raster data with points of the regular grid
    print('Assigning values to each point..')
    for i, row in geo_df.iterrows():
        # population
        if imported_pop.empty:
            if pixel_x_pop <= resolution:
                row_min, column_max = raster_population.\
                    index(row.X + resolution/2, row.Y + resolution/2)
                row_max, column_min = raster_population.\
                    index(row.X - resolution / 2, row.Y - resolution / 2)
                value = population[0, row_min:row_max,
                                   column_min:column_max].sum().sum()
                geo_df.loc[i, 'Population'] = value
            else:
                x, y = raster_population.index(row.X, row.Y)
                # better assign to the center
                geo_df.loc[i, 'Population'] = \
                    population[0, x, y]/pixel_x_pop * resolution
        # road distance
        nearest_geoms = nearest_points(Point(row.X, row.Y), streets_multipoint)
        geo_df.loc[i, 'Road_dist'] = \
            nearest_geoms[0].distance(nearest_geoms[1])

        # elevation
        x, y = raster_elevation_resampled.index(row.X, row.Y)
        geo_df.loc[i, 'Elevation'] = elevation_resampled[0, x, y]

        # slope
        x, y = raster_slope_resampled.index(row.X, row.Y)
        geo_df.loc[i, 'Slope'] = slope_resampled[0, x, y]

        # land cover
        x, y = raster_land_cover.index(row.X, row.Y)
        geo_df.loc[i, 'Land_cover'] = land_cover[0, x, y]

        # protected areas
        if prot_exist:
            geo_df.loc[i, 'Protected_area'] = \
                protected_areas['geometry'].contains(Point(row.X,row.Y)).any()

        print('\r' + str(i) + '/' + str(geo_df.index.__len__()),
              sep=' ', end='', flush=True)

    print('\n')
    geo_df.Elevation = geo_df.Elevation.astype(int)
    pd.DataFrame(geo_df.drop(columns='geometry'))\
        .to_csv('Input/downloaded_csv.csv', index=False)

    return geo_df


def resample(raster, resolution):

    # get pixel size
    affine = raster.transform
    pixel_x = affine[0]
    scale_factor = pixel_x / resolution
    # re-sample data to target shape
    data = raster.read(
        out_shape=(
            raster.count,
            int(raster.height * scale_factor),
            int(raster.width * scale_factor)
        ),
        resampling=Resampling.bilinear
    )

    # scale image transform
    transform = raster.transform * raster.transform.scale(
        (raster.width / data.shape[-1]),
        (raster.height / data.shape[-2])
    )

    profile = raster.profile
    profile.update(transform=transform, width=raster.width * scale_factor,
                   height=raster.height * scale_factor)

    return data, profile
