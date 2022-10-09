from pyomo.environ import Param, RangeSet, Set, Var, Objective, Constraint, minimize,\
    NonNegativeReals, NonNegativeIntegers, Binary

from gisele.michele.constraints_definition import *
from gisele.michele.components_initialization import *

def Model_Creation(model, input_load, wt_prod, pv_prod,ht_prod,input_michele):
    '''
    This function creates the instance for the resolution of the optimization in Pyomo.

    :param model: Pyomo model as defined in the Micro-Grids library.

    '''

    #Data related to set definition

    pv_types = list(range(1,input_michele['pv_types']+1))
    wt_types = list(range(1,input_michele['wt_types']+1))
    bess_types = list(range(1,input_michele['bess_types']+1))
    dg_types = list(range(1,input_michele['dg_types']+1))
    ht_types = list(range(1, input_michele['ht_types'] + 1))

    # Parameters related to set definition
    model.num_days = Param() #number of representative days of 1 year
    model.num_years = Param() #number of years of the project
    model.project_duration = Param(initialize=initialize_project_duration)
    model.h_weight = Param(initialize=initialize_h_weight) # weight of 1 hour (different from 1 if representative days are used)
    model.pv_types = Param()
    model.wt_types = Param()
    model.bess_types = Param()
    model.dg_types = Param()
    model.ht_types=Param()

    #SETS

    model.hours = RangeSet(1, model.project_duration)
    model.hours_last = Set(initialize=initialize_hours_last) #set of last hour of each year
    model.years = RangeSet(1, model.num_years)
    # model.pv = RangeSet(1, model.pv_types)
    # model.wt = RangeSet(1, model.wt_types)
    # model.bess = RangeSet(1, model.bess_types)
    # model.dg = RangeSet(1, model.dg_types)
    model.pv = Set(initialize=[str(n) for n in pv_types])
    model.wt = Set(initialize=[str(n) for n in wt_types])
    model.bess = Set(initialize=[str(n) for n in bess_types])
    model.dg = Set(initialize=[str(n) for n in dg_types])
    model.ht=Set(initialize=[str(n) for n in ht_types])

    #PARAMETERS

    # Parameters of the PV
    model.pv_nominal_capacity = Param(model.pv)  # Nominal capacity of the PV in kW/unit
    model.pv_investment_cost = Param(model.pv)  # Cost of solar panel in €/unit
    model.pv_OM_cost = Param(model.pv)  # Cost of O&M solar panel in €/unit/y
    model.pv_max_units = Param(model.pv)  # Maximum number of installed units [-]
    model.pv_life = Param(model.pv) #Lifetime of panels [y]

    # Parameters of the Wind Turbine
    model.wt_nominal_capacity = Param(model.wt)  # Nominal capacity of the WT in kW/unit
    model.wt_investment_cost = Param(model.wt)  # Cost of WT in €/unit
    model.wt_OM_cost = Param(model.wt)  # Cost of O&M WT in €/unit/y
    model.wt_max_units = Param(model.wt)  # Maximum number of installed units [-]
    model.wt_life = Param(model.wt)  # Lifetime of WT [y]

    # Parameters of the Hydro Turbine

    model.ht_nominal_capacity = Param(model.ht)  # Nominal capacity of the HT in kW/unit
    model.ht_investment_cost = Param(model.ht)  # Cost of HT in €/unit
    model.ht_connection_cost = Param(model.ht)  # Cost of ht interconnection to the MV grid €
    model.ht_OM_cost = Param(model.ht)  # Cost of O&M HT in €/unit/y
    model.ht_max_units = Param(model.ht)  # Maximum number of installed units [-]
    model.ht_life = Param(model.ht)  # Lifetime of HT [y]
    model.ht_P_min = Param(model.ht)  # Minimum power of HT (related to min flow rate) [0-1]
    model.ht_efficiency = Param(model.ht)  # Constant efficiency of HT [0-1]

    # Parameters of the Storage System
    model.bess_nominal_capacity = Param(model.bess)  # Nominal capacity of the BESS in kWh/unit
    model.bess_investment_cost = Param(model.bess)  # Cost of BESS in €/unit
    model.bess_OM_cost = Param(model.bess)  # Cost of O&M BESS in €/unit/y
    model.bess_max_units = Param(model.bess)  # Maximum number of installed units [-]
    model.bess_life = Param(model.bess)  # Lifetime of BESS [y]
    model.bess_cycle_life = Param(model.bess)  # cycling lifetime of BESS [kwh]
    model.bess_depth_of_discharge = Param(model.bess)  # Depth of discharge of the battery (DOD) [0-1]
    model.bess_P_ratio_max = Param(model.bess) #Maximum Ratio of Power/Energy [kW/kWh]
    model.bess_ch_efficiency_nom = Param(model.bess)  # Efficiency of the charge of the battery [0-1]
    model.bess_dis_efficiency_nom = Param(model.bess)  # Efficiency of the discharge of the battery [0-1]
    model.bess_initial_SOC = Param(model.bess) #initiali state of charge [0-1]
    model.bess_wear_cost = Param(model.bess, initialize=Initialize_wear_cost)  # cycling degradation cost [€/kwh]

    # Parameters of the Diesel Generator
    model.dg_nominal_capacity = Param(model.dg)  # Nominal capacity of the DG in kW/unit
    model.dg_investment_cost = Param(model.dg)  # Cost of DG in €/kW
    model.dg_OM_cost = Param(model.dg)  # Cost of O&M DG in €/unit/h
    model.dg_max_units = Param(model.dg)  # Maximum number of installed units [-]
    model.dg_life = Param(model.dg )  # Lifetime of DG [functioning hours]
    model.dg_P_min = Param(model.dg) #Minimum power [0-1]
    model.dg_cost_coeff_A = Param(model.dg) # linear Fuel consumption curve coefficient [l/h]
    model.dg_cost_coeff_B = Param(model.dg) # linear Fuel consumption curve coefficient [l/h/kW]
    model.dg_SU_cost = Param(model.dg)  # Start up cost [€]
    model.dg_SD_cost = Param(model.dg)  # Shut down cost [€]
    model.dg_UT = Param(model.dg) #minimum up time [h]
    model.dg_DT = Param(model.dg) #minimum down time [h]
    model.dg_RU = Param(model.dg) #ramp up limit [kW/h]
    model.dg_RD = Param(model.dg) #ramp down limit [kW/h]
    model.dg_repl_cost = Param(model.dg, initialize=Initialize_dg_repl_cost)  # unitary replacement dg cost [€/h ON]

    # Scalars
    model.inflation_rate=Param() # inflation rate [0-1]
    model.nominal_interest_rate = Param()  # nominal interest rate [0-1]
    model.derating_factor = Param() # to reduce value at end of life [0-1]
    model.ir = Param(initialize=Initialize_ir) # real interest rate [0-1]
    model.discount_rate = Param(model.hours, initialize=Initialize_Discount_Rate) #discount rate [0-1]
    model.lost_load_max = Param()  # maximum admitted loss of load [0-1]
    model.lost_load_value = Param()
    model.fuel_cost = Param() #cost of diesel [€/l]
    model.inverter_cost = Param() #investment cost of inverter [€/kW]
    model.inverter_life = Param() #lifetime of inverter [y]
    model.load_forecast_error = Param() #[0-1]
    model.pv_forecast_error = Param() # error on power produced from pv panels[0-1]
    model.wt_forecast_error = Param()  # [0-1]
    model.demand_growth = Param() #yearly demand growth [0-1]
    model.M = Param() #big number
    model.epsilon = Param() #small number

    #input profiles
    model.input_load = Param(model.hours, initialize=Initialize_load)  # hourly load profile [kWh]
    model.input_pv_prod = Param(model.hours, model.pv, initialize=Initialize_pv_prod)  # hourly PV production [kWh]
    model.input_wt_prod = Param(model.hours, model.wt, initialize=Initialize_wt_prod)  # hourly WT production [kWh]
    model.input_hydro_res = Param(model.hours, model.ht, initialize=Initialize_ht_prod)  # hourly HT production [kWh]

    #VARIABLES

    # Variables associated to the project
    model.initial_investment = Var(within=NonNegativeReals)
    model.OM_cost = Var(within=NonNegativeReals)
    model.replacement_cost = Var(within=NonNegativeReals)
    model.salvage_value = Var(within=NonNegativeReals)

    # Variables associated to RES
    model.pv_units = Var(model.pv, within=NonNegativeReals)  # Number of units of solar panels
    model.wt_units = Var(model.wt,within=NonNegativeIntegers)  # Number of units of wind turbines
    model.total_power_res = Var(model.hours, within=NonNegativeReals)  # Power generated from the PV and WT [kW]

    # Variables associated to the hydro turbine
    model.ht_units = Var(model.ht, within=NonNegativeIntegers)  # Number of installed units of hydro turbine
    model.ht_power = Var(model.hours, model.ht, within=NonNegativeReals)  # Power provided by HT [kWh]
    model.ht_units_on = Var(model.hours, model.ht, within=NonNegativeIntegers)  # number of active HT in h

    # Variables associated to the battery bank
    model.bess_units = Var(model.bess, within=NonNegativeReals)  # Number of units of batteries
    model.bess_dis_power = Var(model.hours, model.bess, within=NonNegativeReals)  # Battery discharging power in kW
    model.bess_ch_power = Var(model.hours, model.bess, within=NonNegativeReals)  # Battery charging power in kW
    model.bess_total_energy = Var(model.hours, model.bess, within=NonNegativeReals) #Battery charge level at h [kWh]
    model.bess_power_max = Var(model.bess, within=NonNegativeReals) #maximum power withdrawn or injected by the batteries [kW]
    model.bess_bin = Var(model.hours, model.bess, within=Binary) #Binary variable, 1 if charging mode

    # Variables associated to the diesel generator
    model.dg_units = Var(model.dg,within=NonNegativeIntegers) # Number of units of diesel generators
    model.dg_power = Var(model.hours, model.dg, within=NonNegativeReals) #Power level the Diesel generator [kWh]
    model.dg_fuel_consumption = Var(model.hours,model.dg,within=NonNegativeReals) #diesel consumption [L]
    model.dg_units_on = Var(model.hours,model.dg, within=NonNegativeIntegers) #number of active DG in h

   # Variables associated to the energy balance
    model.Load = Var(model.hours, within=NonNegativeReals)
    model.lost_load = Var(model.hours, within=NonNegativeReals)  # Power not supplied by the system [kW]
    model.load_total = Var(model.hours, within=NonNegativeReals) # Cumulative energy requirement of the project [kWh]
    model.lost_load_total = Var(model.hours, within=NonNegativeReals)  # Cumulative power not supplied by the system [kWh]

    # Variables associated to reserve needs
    model.reserve = Var(model.hours, within=NonNegativeReals) #total reserve needed per hour [kW]
    model.reserve_dg = Var(model.hours,model.dg, within=NonNegativeReals) #reserve provided by DG [kW]
    model.reserve_bess = Var(model.hours, model.bess, within=NonNegativeReals)  # reserve provided by BESS [kW]

    # OBJETIVE FUNTION:
    model.ObjectiveFuntion = Objective(rule=total_net_present_cost, sense=minimize)

    # CONSTRAINTS
    # to compute OF
    model.TotalInitialInvestment = Constraint(rule=total_initial_investment)
    model.TotalReplacementCost = Constraint(rule=total_replacement_cost)
    model.TotalOMCost = Constraint(rule=total_OM_cost)
    model.TotalSalvageValue = Constraint(rule=total_salvage_value)
    # to design the system
    model.TotalLoad = Constraint(model.hours, rule=total_load)
    model.PvInstalled = Constraint(model.pv, rule=pv_installed)
    model.WtInstalled = Constraint(model.wt, rule=wt_installed)
    model.BessInstalled = Constraint(model.bess, rule=bess_installed)
    model.DgInstalled = Constraint(model.dg, rule=dg_installed)
    model.ResEnergy = Constraint(model.hours, rule=res_energy)
    model.SystemBalance = Constraint(model.hours, rule=system_balance)
    model.TotalEnergyReq = Constraint(model.hours, rule=total_energy_req)
    model.TotalLostLoad = Constraint(model.hours, rule=total_lost_load)
    model.LimitLostLoad = Constraint(model.hours, rule=limit_lost_load)
    model.TotalReserveReq = Constraint(model.hours, rule=total_reserve_req)
    model.ReserveAllocation = Constraint(model.hours, rule=reserve_allocation)
    # constraints related to diesel generators
    model.FuelConsumptionCurve = Constraint(model.hours,model.dg, rule=fuel_consumption_curve)
    model.DgPowerMax = Constraint(model.hours, model.dg, rule=dg_power_max)
    model.DgPowerMin = Constraint(model.hours, model.dg, rule=dg_power_min)
    model.DgOnline = Constraint(model.hours, model.dg, rule=dg_online)
    # constraints related to batteries
    model.BatteryPowerMax = Constraint(model.hours,model.bess, rule=battery_power_max)
    model.BessCondition1 = Constraint(model.hours, model.bess, rule=bess_condition1)
    model.BessCondition2 = Constraint(model.hours, model.bess, rule=bess_condition2)
    model.BessChargingLevel = Constraint(model.hours,model.bess, rule=bess_charging_level)
    model.BessChargingLevelMin = Constraint(model.hours,model.bess, rule=bess_charging_level_min)
    model.BessChargingLevelMax = Constraint(model.hours,model.bess, rule=bess_charging_level_max)
    model.BessChPowerMax = Constraint(model.hours,model.bess, rule=bess_ch_power_max)
    model.BessDisPowerMax = Constraint(model.hours, model.bess, rule=bess_dis_power_max)
    # constraints related to hydro turbine
    model.HtPowerMax = Constraint(model.hours, model.ht, rule=ht_power_max)
    model.HtPowerRiver = Constraint(model.hours, model.ht, rule=ht_power_river)
    model.HtPowerMin = Constraint(model.hours, model.ht, rule=ht_power_min)
    model.HtOnline = Constraint(model.hours, model.ht, rule=ht_online)





