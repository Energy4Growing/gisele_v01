[![Documentation Status](https://readthedocs.org/projects/gisele-v01/badge/?version=main)](https://gisele-v01.readthedocs.io/en/main/?badge=main)
![Screenshot](logo.PNG)

# About

The GIS for electrification (Gisele) tool was developed as an effort to improve the planning of rural electrification in developing countries. It is an open source Python-based tool that uses GIS and terrain analysis to model the area under study, groups loads using a density-based clustering algorithm called DBSCAN and then it uses graph theory to find the least-costly electric network topology that can connect all the people in the area. 

The methodology of Gisele consists in three main steps: data analysis, clustering and grid routing. During the initial phase of data gathering and analysis, GIS data sets are created in order to properly map several information about the area to be electrified. Some of these information are: population density, elevation, slope and roads. They are all processed using a weighting strategy that translates the topological aspect of the terrain to the difficulty of line deployment. Then, DBSCAN is used to strategically aggregates groups of people in small areas called clusters. The output is a set number of clusters, partially covering the initial area considered, in which the grid routing algorithm is performed. Finally, Gisele uses the concept of Steiner tree to create a network topology connecting all the aggregated people in each cluster, and then, if necessary, it makes use of Dijkstra’s algorithm to connect each cluster grid into an existing distribution network.

# Requirements
* Python 3.7
* Solver for MILP optimization: the default is 'gurobi'

# Getting started
Once having downloaded Python and cloned/download the project, it is possible to automatically create the environment with the useful packages by running in the command prompt:

```
conda env create -f environment.yml
```
Run 
```
Gisele.py
```
Gisele is provided by a user interface which can be accessed by clicking on the link that appears on the console, or directly opening the page http://127.0.0.1:8050/ in a web browser.
For more information see the documentation in Gisele/docs

# Documentation
Documentation is available at: https://gisele-v01.readthedocs.io/en/main/

# Contributing
Anybody is welcome to contribute to the project! The main steps to follow are:

* Fork the project on GitHub
* Create a feature branch to work on in your fork (git checkout -b new-feature)
* Add your name to the AUTHORS file
* Commit your changes to the feature branch
* Push the branch to GitHub (git push origin my-new-feature)
* On GitHub, create a new pull request from the feature branch

# Citing 
Please cite Gisele referring to the following journal publication:
Corigliano, S., Carnovali, T., Edeme, D., & Merlo, M. (2020). Holistic geospatial data-based procedure for electric network design and least-cost energy strategy. Energy for Sustainable Development, 58, 1-15. https://doi.org/10.1016/j.esd.2020.06.008

# Licencing

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License



