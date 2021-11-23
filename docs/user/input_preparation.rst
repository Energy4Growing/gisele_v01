.. _input_preparation:

============================
Input data preparation
============================
In the folder *input_preparation* there is a python script that can help in the automatic generation of the csv file, required as input
in the geospatial processing step.
To use it, please follow the following steps:

* Identify the study area and create a polygon shapefile that surrounds it;
* Save the shapefile inside the folder 'input_preparation' as 'case_study/study_area.shp': case_study is a new folder with a name of choice for the case study;
* Create a 'database' folder, with the same subfolders and files as the folder 'mocuba': the files are the source files that will be cropped for the desired case_study area;
* Change the parameters in the file 'input-config.csv': crs, the epsg code of the projected coordinate reference system for the area; resolution, the desired resolution for the grid of points in Gisele; case_study, the name of the case_study folder created; database, the name of the database folder created.
* Run *input_preparation.py*;
* Retrieve the csv file with the regular grid of points from the 'case_study/Output' folder.
