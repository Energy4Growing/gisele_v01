from math import sqrt
import numpy as np
import pandas as pd

# initialize parameters for set definition


def initialize_project_duration(model):
    return model.num_days * model.num_years * 24


def initialize_h_weight(model):
    return 8760//(model.num_days * 24)


# initialize sets
def initialize_hours_last(model):
    return (h for h in model.hours if h%(model.num_days * 24)==0)


# initialize parameters
def Initialize_wear_cost(model,b):
    return model.bess_investment_cost[b] / (model.bess_cycle_life[b] * sqrt(model.bess_ch_efficiency_nom[b] * model.bess_dis_efficiency_nom[b]))


def Initialize_dg_repl_cost(model,g):
    return model.dg_investment_cost[g] / model.dg_life[g]


def Initialize_ir(model):
    return (model.nominal_interest_rate - model.inflation_rate) / (1 + model.inflation_rate)


def Initialize_Discount_Rate(model, h):
    return 1 / (1+model.ir)**(h//(model.num_days * 24))


def importing(load_profile, pv_avg, wt_avg,ht_avg):
    global input_load, wt_prod, pv_prod, ht_prod

    input_load = pd.DataFrame(data=list(load_profile),
                              index=np.arange(1, load_profile.size+1),
                              columns=['DT'])
    # input_load = pd.read_csv(r'C:\Users\Vinicius\PycharmProjects\Gisele-full-version\gisele\michele\Inputs\load_Soroti_12repdays.csv')
    # input_load = pd.read_csv('gisele\michele\Inputs\load_Soroti_12repdays.csv')
    # input_load.set_index('h', inplace=True)

    pv_prod = pd.DataFrame(data=list(pv_avg[0]),
                           index=np.arange(1, pv_avg.size + 1),
                           columns=['1'])

    # pv_prod = pd.read_csv(r'C:\Users\Vinicius\PycharmProjects\Gisele-full-version\gisele\michele\Inputs\solarPV_Soroti_12repdays.csv')
    # pv_prod.set_index('h', inplace=True)

    # wt_prod = pd.read_csv(r'C:\Users\Vinicius\PycharmProjects\Gisele-full-version\gisele\michele\Inputs\windPower_Soroti_12repdays.csv')
    # wt_prod.set_index('h', inplace=True)
    #
    wt_prod = pd.DataFrame(data=list(wt_avg[0]),
                           index=np.arange(1, wt_avg.size + 1),
                           columns=['1'])

    ht_prod = pd.DataFrame(data=ht_avg.values,

                           index=np.arange(1, len(ht_avg[0]) + 1),

                           columns=[str(x + 1) for x in ht_avg.columns])

    return input_load, wt_prod, pv_prod, ht_prod

def Initialize_load(model, h):

    return input_load.loc[h, 'DT']


def Initialize_pv_prod(model,h, p):
    return pv_prod.loc[h, str(p)]


def Initialize_wt_prod(model, h, p):
    return wt_prod.loc[h, str(p)]

def Initialize_ht_prod(model,h,p):
    return ht_prod.loc[h,str(p)]



