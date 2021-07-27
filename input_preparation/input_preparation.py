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
from gisele import initialization

# Define the function resample
def resample(raster, resolution,options):
    ''' This functions resamples a given raster according to the selected parameters. It should mostly used for decreasing the resolution.
    As input, the function accepts the following:
    raster -> the existing raster file
    resolution -> preffered resolution of the new file
    options -> method to be used in the resampling

    It returns the new raster file with the preffered resolution and options (not actually useful for anything)'''
    # get pixel size
    affine = raster.transform
    pixel_x = affine[0]
    scale_factor = pixel_x / resolution
    # re-sample data to target shape
    if options == 'average': # resample according to the average value
        data = raster.read(
            out_shape=(
                raster.count,
                int(raster.height * scale_factor),
                int(raster.width * scale_factor)
            ),
            resampling=Resampling.average
        )
    elif options == 'mode': #Resample according to the most frequent element
        data = raster.read(
            out_shape=(
                raster.count,
                int(raster.height * scale_factor),
                int(raster.width * scale_factor)
            ),
            resampling=Resampling.mode
        )
    else:
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

def create_grid(crs,resolution,study_area):
    ''' This function creates a grid of points, returning a geopanda dataframe. The input is the following:
    crs -> The preffered crs of the dataframe (according to the case study), input should be an integer.
    resolution -> The preffered resolution of the grid of points, input should be an integer.
    study_area -> This is a shapely polygon, that has to be in the preffered crs.
    '''
    # crs and resolution should be a numbers, while the study area is a polygon
    df = pd.DataFrame(columns=['X', 'Y'])
    min_x=float(study_area.bounds['minx'])
    min_y=float(study_area.bounds['miny'])
    max_x=float(study_area.bounds['maxx'])
    max_y = float(study_area.bounds['maxy'])
    # create one-dimensional arrays for x and y
    lon = np.arange(min_x, max_x, resolution)
    lat = np.arange(min_y, max_y, resolution)
    lon, lat = np.meshgrid(lon, lat)
    df['X'] = lon.reshape((np.prod(lon.shape),))
    df['Y'] = lat.reshape((np.prod(lat.shape),))
    geo_df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.X, df.Y),
                            crs=crs)
    geo_df_clipped = gpd.clip(geo_df,study_area)
    #geo_df_clipped.to_file(r'Test\grid_of_points.shp')
    return geo_df_clipped

def rasters_to_points(study_area,crs,resolution_points,dir,protected_areas,streets):
    '''This function creates a dataframe and a geodataframe with a grid of points for the area of interest. First, it
    creates an empty grid of points and adds attributes to it using rasters. For each attribute(population,
    elevation,slope,landcover,protected areas, road proximity) it reads the raster/shape file and assigns the appropriate
    value to each point of the grid. Throughout the function, rasters/shapes are read(in the correct crs) and are
    resampled using the "resample" function. Then, the sampling is performed. The final output is a geodataframe of the
    grid of points in the desired crs. The input is the following:

    study_area -> This is a shapely polygon, that has to be in the preffered crs.
    crs -> Preffered crs, input should be an integer.
    resolution_points -> Prefered resolution of the new grid of points, should be an integer.
    protected_areas -> Shape file with the protected areas in the desired crs.
    streets -> Shape file with the roads in the desired crs.
    resolution_population -> The resolution of the population raster (should be mostly automatic)
    '''

    '''Create an empty grid of points using the "create_grid" function from this same file.'''
    pointData = create_grid(crs,resolution_points,study_area)
    pointData=pointData.to_crs(crs)
    '''Read all the rasters '''
    # Population
    population_Raster=rasterio.open(dir+'/Input/Population_' + str(crs) + '.tif')
    resolution_population = population_Raster.transform[0]
    data_population, profile_population = resample(population_Raster, resolution_points,'average')
    with rasterio.open(dir+'/Input/Population_resampled.tif',
                     'w', **profile_population) as dst:
        dst.write(data_population)
    Population = rasterio.open(dir+'/Input/Population_resampled.tif')
    ratio=Population.transform[0]/resolution_population

    # Elevation
    elevation_Raster = rasterio.open(dir+'/Input/Elevation_' + str(crs) + '.tif')
    data_elevation, profile_elevation = resample(elevation_Raster, resolution_points,'bilinear')
    with rasterio.open(dir+'/Input/Elevation_resampled.tif',
                     'w', **profile_elevation) as dst:
        dst.write(data_elevation)
    #resolution_elevation = elevation_Raster.transform[0]
    Elevation = rasterio.open(dir+'/Input/Elevation_resampled.tif')

    # Slope
    slope_Raster = rasterio.open(dir+'/Input/Slope_' + str(crs) + '.tif')
    data_slope, profile_slope = resample(slope_Raster, resolution_points,'bilinear')
    with rasterio.open(dir+'/Input/Slope_resampled.tif',
                     'w', **profile_slope) as dst:
        dst.write(data_slope)
    Slope = rasterio.open(dir+'/Input/Slope_resampled.tif')

    #Landcover
    landcover_Raster = rasterio.open(dir+'/Input/LandCover_' + str(crs) + '.tif')
    data_landcover, profile_landcover = resample(landcover_Raster, resolution_points,'mode')
    with rasterio.open(dir+'/Input/Landcover_resampled.tif',
                     'w', **profile_landcover) as dst:
        dst.write(data_landcover)
    LandCover = rasterio.open(dir+'/Input/Landcover_resampled.tif')
    resolution_landcover=landcover_Raster.transform[0]

    '''Create a dataframe for the final grid of points '''
    df = pd.DataFrame(columns=['ID', 'X', 'Y', 'Elevation', 'Slope',
                           'Population', 'Land_cover', 'Road_dist',
                           'River_flow', 'Protected_area'])


    '''Sample the rasters '''
    coords = [(x, y) for x, y in zip(pointData.X, pointData.Y)]
    pointData = pointData.reset_index(drop=True)
    pointData['ID'] = pointData.index
    pointData['Elevation'] = [x[0] for x in Elevation.sample(coords)]
    pointData.loc[pointData.Elevation<0,'Elevation']=0
    print('Elevation finished')
    pointData['Slope'] = [x[0] for x in Slope.sample(coords)]
    print('Slope finished')
    pointData['Population'] = [x[0]*pow(ratio,2) for x in Population.sample(coords)]
    pointData['Population']=pointData['Population'].round(decimals=0)
    print('Population finished')
    pointData['Land_cover'] = [x[0] for x in LandCover.sample(coords)]
    print('Land cover finished')
    pointData['Protected_area'] = [ x for x in protected_areas['geometry'].contains(pointData.geometry)]
    print('Protected area finished')
    #nearest_geoms = nearest_points(pointData.geometry, streets)
    #pointData['Road_dist'] = [ x for x in nearest_geoms[0].distance(nearest_geoms[1])]
    #pointData.to_csv('Test/test.csv')
    '''Start iterating through the points to assign values from each raster  regarding distance to roads'''
    road_distances=[]
    for index, point in pointData.iterrows():
        #print(point['geometry'])
        #print(point['geometry'].xy[0][0],point['geometry'].xy[1][0])
        x = point['geometry'].xy[0][0]
        y = point['geometry'].xy[1][0]
        '''Sample population in that exact same point(maybe we will need to find it as the average of the 9 points around'''
        #row, col = Population.index(x,y)
        #Pop=Population.read(1)[row,col]*pow(ratio,2) # because the population was resampled according to the average value, now we need to multiply

        #row, col= Elevation.index(x,y)
        #elevation = Elevation.read(1)[row,col]

        #row, col = Slope.index(x,y)
        #slope= Slope.read(1)[row,col]

        #row, col = LandCover.index(x,y)
        #landcover=LandCover.read(1)[row,col]

        #protected=protected_areas['geometry'].contains(Point(x,y)).any()

        nearest_geoms = nearest_points(Point(x,y), streets)
        road_distance = nearest_geoms[0].distance(nearest_geoms[1])
        road_distances.append(road_distance)
        #print(index)
        print('\r' + str(index) + '/' + str(pointData.index.__len__()),
              sep=' ', end='', flush=True)
        '''Add a point in the starting dataframe with all the information '''
        #df2 = pd.DataFrame([[int(index),x,y,elevation,slope,round(Pop),landcover,road_distance,0,protected]],
        #                    columns=['ID', 'X', 'Y', 'Elevation', 'Slope',
        #                        'Population', 'Land_cover', 'Road_dist',
        #                        'River_flow', 'Protected_area'])
        #df=df.append(df2)
    pointData['Road_dist']=road_distances
    pointData['River_flow'] = ""

    geo_df = gpd.GeoDataFrame(pointData, geometry=gpd.points_from_xy(pointData.X, pointData.Y),
                               crs=crs)


    return pointData, geo_df

def locate_file(database,folder,extension):
    '''This function locates a file's name just based on an extension and data on the location of the file.
    The point is that in the specific folder, only one file with such extension may exist. The idea is that we might not
    know the exact name of the file, but if we know it's only one file and we know it's extension -> we can find out its
    name. As input, the function accepts:

    database -> The location of the main database
    folder -> The name of the folder we want to look in, actually this is the attribute that we are interested in (elevation,
    slope,population etc).'''
    root = database + '/' + folder
    for file in os.listdir(root):
        if extension in file:
            path = os.path.join(root, file)
            return path
'''Set parameters for the analysis - by the user'''

def create_input_csv():
    #crs=21095
    '''THIS IS THE MAIN FUNCTION OF THIS SCRIPT. It is in charge of creating a weighted grid of points for the area of interest.
    It saves the grid of points in the desired folder, but also returns it as a geodataframe. A grid of points is created with a buffer of
    around 500m around the polygon. The input is as follows:

    crs -> Desired crs, input should be an integer.
    resolution -> Desired resolution for the MV grid_routing, input should be an integer.
    resolution_population -> Resolution of the population raster, which in turn is also the resolution for the low voltage grid routing
    landcover_option -> This is a string with the preffered landcover_option, something that is chosen in the confinguration file.
    country -> Name of the country that we are analysing.It is important that the name matches a folder in the database.
    case_study -> A name for the case study previously chosen by the user.
    database -> The location of the database where all the raster/shape files are stored for the country.
    study_area -> A shapely polygon of the area of interest, it has to be in the preffered crs.'''

    '''Data processing'''
    #database=r'Database/'+country
    input_data = pd.read_csv('input_config.csv',index_col='option')
    database = input_data.loc['database','value']
    crs= int(input_data.loc['crs','value'])
    resolution = int(input_data.loc['resolution', 'value'])
    case_study = input_data.loc['case_study', 'value']

    crs_str=r'epsg:'+str(crs)
    # Open the roads, protected areas and rivers
    protected_areas_file=locate_file(database,folder='Protected_areas',extension='.shp')
    protected_areas = gpd.read_file(protected_areas_file)
    protected_areas = protected_areas.to_crs(crs)

    rivers_file = locate_file(database, folder='Rivers',
                                       extension='.shp')
    rivers = gpd.read_file(rivers_file)
    rivers = rivers.to_crs(crs)
    rivers = rivers[rivers['DIS_AV_CMS']>2] # todo -> make this number reasonable

    roads_file=locate_file(database,folder='Roads',extension='.shp')
    streets = gpd.read_file(roads_file)

    streets = streets.to_crs(crs)
    study_area = gpd.read_file(case_study+'/study_area.shp')
    study_area_crs=study_area.to_crs(crs)
    dir=case_study
    if not os.path.exists(dir+'/Input'):
        os.makedirs(dir+'/Input')
    if not os.path.exists(dir + '/Output'):
        os.makedirs(dir + '/Output')
    # Create a small buffer to avoid issues
    study_area_buffered=study_area.buffer((resolution*0.1/11250)/2)

    study_area_buffered_list=[study_area_buffered] # this is to fix the issue with Polygon not being iterable when using rasterio
    '''Clip the protected areas'''
    protected_areas_clipped=gpd.clip(protected_areas,study_area_crs)
    streets_clipped = gpd.clip(streets,study_area_crs)
    rivers_clipped = gpd.clip(rivers, study_area_crs)
    if not streets_clipped.empty:
        streets_clipped.to_file(dir+'/Input/Roads.shp')

    if not protected_areas_clipped.empty:
        protected_areas_clipped.to_file(dir+'/Input/protected_area.shp')

    if not rivers_clipped.empty:
        rivers_clipped.to_file(dir + '/Input/Rivers.shp')
    '''Clip the elevation and then change the crs'''

    elevation_file=locate_file(database,folder='Elevation',extension='.tif')
    with rasterio.open(elevation_file,

            mode='r') as src:
        out_image, out_transform = rasterio.mask.mask(src, study_area_buffered.to_crs(src.crs), crop=True)
        print(src.crs)

    out_meta = src.meta
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

    with rasterio.open(dir+'/Input/Elevation.tif', "w", **out_meta) as dest:
        dest.write(out_image)
    input_raster = gdal.Open(dir+'/Input/Elevation.tif')
    output_raster = dir+'/Input/Elevation_' + str(crs) + '.tif'
    warp = gdal.Warp(output_raster, input_raster, dstSRS=crs_str)
    warp = None  # Closes the files

    '''Clip the slope and then change the crs'''

    slope_file = locate_file(database, folder='Slope', extension='.tif')
    with rasterio.open(slope_file,

            mode='r') as src:
        out_image, out_transform = rasterio.mask.mask(src, study_area_buffered.to_crs(src.crs), crop=True)
        print(src.crs)

    out_meta = src.meta
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

    with rasterio.open(dir+'/Input/Slope.tif', "w", **out_meta) as dest:
        dest.write(out_image)
    input_raster = gdal.Open(dir+'/Input/Slope.tif')
    output_raster = dir+'/Input/Slope_' + str(crs) + '.tif'
    warp = gdal.Warp(output_raster, input_raster, dstSRS=crs_str)
    warp = None  # Closes the files

    '''Clip the population and then change the crs'''

    population_file = locate_file(database, folder='Population', extension='.tif')
    with rasterio.open(
            population_file,

            mode='r') as src:
        out_image, out_transform = rasterio.mask.mask(src, study_area_buffered.to_crs(src.crs), crop=True)
        print(src.crs)

    out_meta = src.meta
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

    with rasterio.open(dir+'/Input/Population.tif', "w", **out_meta) as dest:
        dest.write(out_image)
    # for now there is no need since the population is already in the desired crs
    input_raster = gdal.Open(dir+'/Input/Population.tif')
    output_raster = dir+'/Input/Population_' + str(crs) + '.tif'
    warp = gdal.Warp(output_raster, input_raster, dstSRS=crs_str)
    warp = None  # Closes the files

    '''Clip the land cover and then change the crs'''

    landcover_file = locate_file(database, folder='LandCover', extension='.tif')
    with rasterio.open(
            landcover_file,

            mode='r') as src:
        out_image, out_transform = rasterio.mask.mask(src, study_area_buffered.to_crs(src.crs), crop=True)
        print(src.crs)

    out_meta = src.meta
    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

    with rasterio.open(dir+'/Input/LandCover.tif', "w", **out_meta) as dest:
        dest.write(out_image)
    input_raster = gdal.Open(dir+'/Input/LandCover.tif')
    output_raster = dir+'/Input/LandCover_' + str(crs) + '.tif'
    warp = gdal.Warp(output_raster, input_raster, dstSRS=crs_str)
    warp = None  # Closes the files

    '''This part transforms the roads from lines to multi points.'''
    streets_points = []
    for line in streets_clipped['geometry']:
        # print(line.geometryType)
        if line.geometryType() == 'MultiLineString':
            for line1 in line:
                for x in list(zip(line1.xy[0], line1.xy[1])):
                    # print(line1)
                    streets_points.append(x)
        else:
            for x in list(zip(line.xy[0], line.xy[1])):
                # print(line)
                streets_points.append(x)
    streets_multipoint = MultiPoint(streets_points)

    # Finally, using the "rasters_to_points" function, create and populate the grid of points for the area of interest.
    df, geo_df = rasters_to_points(study_area_crs, crs, resolution, dir,protected_areas_clipped,streets_multipoint)
    geo_df.to_file(dir+'/Input/grid_of_points.shp')

    geo_df=geo_df.reset_index(drop=True)
    geo_df['ID']=geo_df.index
    df=df.reset_index(drop=True)
    df['ID']=df.index

    df.to_csv(dir+'/Output/grid_of_points.csv', index=False)
    return
def delete_leftover_files(dir,crs):
    folder = dir+'/Input/'
    os.remove(folder+'Elevation.tif')
   # os.remove(folder + 'Elevation_'+str(crs)+'.tif')
    os.remove(folder + 'LandCover.tif')
   # os.remove(folder + 'LandCover_'+str(crs)+'.tif')
    os.remove(folder + 'Population.tif')
    #os.remove(folder + 'Population_'+str(crs)+'.tif')
    os.remove(folder + 'Slope.tif')
    #os.remove(folder + 'Slope_' + str(crs) + '.tif')

if __name__ == "__main__":
    create_input_csv()