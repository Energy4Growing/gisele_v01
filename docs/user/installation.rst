.. _installation:

=========================
Download and installation
=========================

Requirements
============

Gisele has been tested on Windows.

Running Gisele requires what follows:

1. The Python programming language, version 3.7 or higher.
2. A number of Python add-on modules .
3. A solver: Gisele has been tested Gurobi; any other solver that is compatible with Pyomo should also work.
4. The Gisele software itself.
5. Login to Earth Engine website if GIS data need to be downloaded automatically

Recommended installation method
===============================

Clone or download the GitHub project folder.
The easiest way to get a working Gisele installation is to use the free ``conda`` package manager.

To get ``conda``, `download and install the "Miniconda" distribution for your operating system <https://conda.io/miniconda.html>`_ (using the version for Python 3).

With Miniconda installed, you can create a new environment called ``"gisele"`` with all the necessary modules, by running the following command in a terminal or command-line window

  .. code-block:: fishshell

    $ conda env create -f environment.yml

To use Gisele, you need to activate the ``gisele`` environment each time

  .. code-block:: fishshell

    $ conda activate gisele

You are now ready to use Gisele together with the free and open source GLPK solver. However, we recommend to not use this solver where possible, since it performs relatively poorly (both in solution time and stability of result). Indeed, our example models use the free and open source CBC solver instead, but installing it on Windows requires an extra step. Read the next section for more information on installing alternative solvers.


.. _install_solvers:

Solvers
=======

You need at least one of the solvers supported by Pyomo installed. Gurobi (commercial) or CPLEX(commercial) are recommended for large problems. Refer to the documentation of your solver on how to install it.
The default solver is gurobi. To change it to one of the solver you downloaded you need to go inside two files:

1. gisele/michele/model_solve.py, line 20, and write the name of the solver instead of 'gurobi'.
2. gisele/lcoe_optimization.py, line 158, and write the name of the solver instead of 'gurobi'.

CBC
---

GLPK
----
GLPK is a free solver, easily integrable inside python. It is less powerful than
the other solvers and might easily have convergence isssues.
To install it, write in the command prompt:

.. code-block:: fishshell

    $ conda install -c conda-forge glpk



Gurobi
------
Gurobi is a powerful commercial solver, that can be downloaded with a free academic
licence if the user is a student.
To install it register on the website: https://www.gurobi.com/ (Academic registration for free products)
and follow the instruction for downloading Gurobi solver: https://www.gurobi.com/downloads/gurobi-optimizer-eula/
Finally, request and activate the Licence (https://www.gurobi.com/downloads/end-user-license-agreement-academic/)
Gurobi solver should be automatically saved within the environment variables and python should be able to use it automatically

CPLEX
-----



Google Earth Engine
===============================
When the option automatic data download is activated in Gisele, GIS data are
downloaded from free APIs.
Many of the data come from Google Earth Engine database that can be accessed via the following steps:

1. Sign up into Google Earth Engine: https://signup.earthengine.google.com/
2. Install earth engine Python package in gisele environment (if the environment has been created through the environment.yml file, skip this step)

    .. code-block:: fishshell

        $ conda install -c conda-forge earthengine-api
3. Authenticate:  from Python terminal, once gisele environment is activated, type:

    .. code-block:: fishshell

        $ earthengine authenticate

