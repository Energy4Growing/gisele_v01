.. _running:

=========================
Running Gisele
=========================
Graphical User Interface
------------------------
To start Gisele Graphical User Interface, run the file 'Gisele.py'.
By clicking on the link that appears, a window in the browser opens at the address:

The procedure is divided into different steps, corresponding to the tabs.

.. toctree::
   :maxdepth: 2
    geospatial_data_processing
    clustering
    grid_routing
    microgrid_sizing
    npc_analysis

To procede in the steps the first time it is run, it is necessary to start from the beginning and in each tab, after selecting the proper options and loading the neccessary files press the button *run*. This make the code process the data and provide some output for the step in analysis. After output are created and loaded it is possible to press the button *next* and go to the following step.


.. warning::

    When the button *run* in a specific tab is pressed, all the output files related to the subsequent steps are deleted.
    The files in related to the previous steps are instead kept in the Output folder

.. warning::

    In any  of the tabs, if buttons are not touched, the options saved in the previous run are used. So even if some options seem to be deactivated, they may not. So every time you want to make sure of a certain number or option, type it again.

.. note::
    When the button *run* in a specific tab is pressed, all the output files related to the subsequent steps are deleted.
    The files in related to the previous steps are instead kept in the Output folder

Input data
----------
Input data are located inside the folder 'Input'.

Output data
-----------
Output data are locate inside the folder 'Output'.
They are csv files or shapefiles, that can be visualized in a software like QGIS


