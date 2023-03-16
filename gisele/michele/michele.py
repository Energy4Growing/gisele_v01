from pyomo.environ import AbstractModel, Var, value

from gisele.michele.components_creation import Model_Creation
from gisele.michele.model_solve import Model_Resolution
from gisele.michele.results import Load_results
from gisele.michele.components_initialization import importing


def start(load_profile, pv_avg, wt_avg,input_michele,ht_avg):
    input_load, wt_prod, pv_prod,ht_prod = importing(load_profile, pv_avg, wt_avg,ht_avg)

    model = AbstractModel()  # define type of optimization problem

    # Optimization model
    print('Starting model creation')
    Model_Creation(model, input_load, wt_prod, pv_prod,ht_prod,input_michele)  # Creation of the Sets, parameters and variables.
    print('Starting model resolution')
    instance = Model_Resolution(model)  # Resolution of the instance

    print('Show results')

    inst_pv, inst_wind, inst_dg, inst_hydro, inst_bess, inst_inv, init_cost, rep_cost, \
        om_cost, salvage_value, gen_energy, load_energy, dg_fuel,lost_load \
        = Load_results(instance)

    return inst_pv, inst_wind, inst_dg,inst_hydro, inst_bess, inst_inv, init_cost, \
        rep_cost, om_cost, salvage_value, gen_energy, load_energy, dg_fuel,lost_load



