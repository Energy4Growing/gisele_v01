.. _Microgrid sizing:

============================
Microgrid sizing
============================

The goal of this step is optimally design a hybrid microgrid for each cluster.
The algorithm is a MILP optimizer, named 'michele', that is found inside the gisele folder.
Only some of the data can be changed from the user interface, while many of them need to be changed manually in the text file: *gisele/michele/Inputs/data.json*

**Files to be loaded**

* Load profile: it is the specific load curve (per unit power) of each person. It will be multiplied by the peak power defined in the grid routing procedure

**Options**

* Wind turbine type: it is possible to choose among different types of wind turbines, that have different nominal power/wind speed curves


