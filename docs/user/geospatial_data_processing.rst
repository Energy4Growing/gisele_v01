.. _geospatial data processing:

============================
Geospatial data processing
============================

The goal of this step is to gather geospatial data related to the area of interest and to process them to create a 'weighted grid of points',
where to each point is associated the population and a weight, dependent on type of terrain.

**Files to be loaded**

**Options**

* Download GIS data: in case this option is active, data are automatically downloaded from online databases.
  *Insert coordinates (degrees) of a square surrounding the area of interest
  *Import population: in case this option is active, it is possible to load a csv file with the point indicating the population. The rest of the layers will be loaded automatically

.. note::
    To use this option it is neccessary to have the login into Earth Engine website, as explained in the installation page

* CRS: the epsg code of the used coordinate reference system. It must be a crs with coordinates expressed in meters. E.g. in case the code is epsg: 32737, type 32737
* Resolution: desired resolution [m] of the grid of points (the weighted surface). The higher the number, the faster the simulations, the lower the accuracy
* Landcover dataset: the name of landcover dataset used, necessary to provide the correct weight.

**Output**

The Output is shown in the map: a point vector layer, with a weight and population associated to each point.
The table with the carachteristics of each point is also reported
The file is saved as a csv inside the folder *'Input'*, with a name imported
