# -*- coding: utf-8 -*-
"""
Created on Thu Jun 16 11:19:17 2022

@author: Panitz
"""


### Inputs: ####
# Solver-Inputs:
gapFrac        = 0.02
timelimit      = 3600
solver_name    = 'gurobi'

import numpy as np
import datetime

    
####################### kleine Daten zum Test ###############################
Q_th_Last = np.arange(0,35,1)
   
# 5 Zeitschritte
aTimeSeries = [datetime.datetime(2020, 1,1)] +  np.arange(5) * datetime.timedelta(hours=1)
aTimeSeries = aTimeSeries.astype('datetime64')
##########################################################################

from flixStructure import *
from flixComps    import *

print('#######################################################################')
print('################### start of modeling #################################')

calc_list = []
nominal_val_list = []
investcosts_segmented_list= []

for a_Q_th_Last in Q_th_Last:
  # Busse:
  #                 Typ         Name              
  Fernwaerme = cBus('th'        ,'Waerme', excessCostsPerFlowHour=100);
  Gas        = cBus('fuel'      ,'Gas'   , excessCostsPerFlowHour=100);
  
  costs = cEffectType('costs','€'      , 'Kosten', isStandard = True, isObjective = True)
  
  costsInInvestSizeSegs = [[5, 10, 15, 20, 20, 30],
                           [6, 11, 16, 21, 21, 25]]
  investArgs = cInvestArgs(investmentSize_is_fixed = False, costsInInvestsizeSegments = costsInInvestSizeSegs,)
  
  # invest_Gaskessel = None #
  gaskessel = cKessel('Kessel', eta  = 0.9,  
                      Q_th = cFlow(label   = 'Q_th', bus = Fernwaerme, investArgs = investArgs, nominal_val=None, min_rel = 1),
                      Q_fu = cFlow(label   = 'Q_fu', bus = Gas))
  
  aWaermeLast       = cSink  ('Wärmelast',sink   = cFlow('Q_th_Last', bus = Fernwaerme, val_rel = a_Q_th_Last, nominal_val=1))
  
  aGasTarif         = cSource('Gastarif', source = cFlow('Q_Gas', bus = Gas, costsPerFlowHour=1))
  
  # Zusammenführung:
  es = cEnergySystem(aTimeSeries)
  es.addEffects(costs)
  es.addComponents(gaskessel, aWaermeLast, aGasTarif)
  
  aCalc = cCalculation('Sim1', es, 'pyomo')
  aCalc.doModelingAsOneSegment()
  
  solverProps = {'solver': solver_name,
                 'displaySolverOutput':False} # nur gurobi!
  
  aCalc.solve(solverProps, nameSuffix = '_' + solver_name, saveResults = False)
  
  # collecting results:
  
  nominal_val_list.append(aCalc.results_struct.Kessel.Q_th.invest.nominal_val)
  investcosts_segmented_list.append(aCalc.results_struct.Kessel.Q_th.invest.investCosts_segmented_costs)
  calc_list.append(aCalc)
  
  
# Plotting: #

import matplotlib.pyplot as plt



plt.scatter(Q_th_Last, nominal_val_list,marker='.',label = 'nominal_val')
plt.scatter(Q_th_Last, investcosts_segmented_list,marker='.',label='costs')
plt.legend()
plt.grid()
plt.show()


# Testing #
soll = [0.0,
 0.0,
 0.0,
 6.0,
 6.0,
 6.0,
 7.0,
 8.0,
 9.0,
 10.0,
 11.0,
 11.0,
 11.0,
 16.0,
 16.0,
 16.0,
 17.0,
 18.0,
 19.0,
 20.0,
 20.999999999999996,
 21.4,
 21.8,
 22.2,
 22.599999999999998,
 23.0,
 23.4,
 23.799999999999997,
 24.2,
 24.599999999999998,
 25.0,
 25.0,
 25.0,
 25.0,
 25.0]


if np.all( np.around(soll) == np.around(investcosts_segmented_list)):
  print('### segmentedLinear Test ok ###')
else:
  raise Exception('## segmentedInvest Test NICHT ok ##')