# -*- coding: utf-8 -*-
"""
Created on Thu Jun 16 11:19:17 2022

@author: Panitz
"""
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 11:26:10 2020

@author: Panitz
"""

# mögliche Testszenarien für testing-tool:
   # abschnittsweise linear testen
   # Komponenten mit offenen Flows 
   # Binärvariablen ohne max-Wert-Vorgabe des Flows (Binärungenauigkeitsproblem)
   # Medien-zulässigkeit 
   
# TODO:
    #  Effektbeispiel mit Anzahl (z.b. Kesselanzahl < 3) 

### Inputs: ####
# Solver-Inputs:
displaySolverOutput = False # ausführlicher Solver-Output.
displaySolverOutput = True  # ausführlicher Solver-Output.
gapFrac        = 0.002
timelimit      = 3600
solver_name    = 'gurobi'
nrOfThreads    = 1
# solver_name    = 'cbc'

### Durchführungs-Optionen: ###
# doSegmentedCalc = True
doSegmentedCalc  = False
checkPenalty    = False  
# importbycsv     = True
################

import os
import matplotlib.pyplot as plt
import time
import json
import numpy as np
import datetime


####################### kleine Daten zum Test ###############################
P_el_Last = [70., 80., 90., 90 , 90 , 90, 90, 90, 90]
if checkPenalty :
    Q_th_Last = [30., 0., 90., 110, 160 , 20, 20, 20, 20]
else :
    Q_th_Last = [30., 0., 90., 110, 110 , 20, 20, 20, 20]
# p_el      = [40., 70., 40., 40 , 40, 40, 70, 70, 70]
p_el      = [40., 40., 40., 40 , 40, 40, 40, 40, 40]
p_el      = np.array(p_el)

   
# todo: ggf. Umstellung auf numpy: aTimeSeries = datetime.datetime(2020, 1,1) +  np.arange(len(Q_th_Last)) * datetime.timedelta(hours=1)
aTimeSeries = datetime.datetime(2020, 1,1) +  np.arange(len(Q_th_Last)) * datetime.timedelta(hours=1)
aTimeSeries = aTimeSeries.astype('datetime64')
nrOfTimeSteps = 9
    
# DAtenreihen kürzen:
P_el_Last = P_el_Last[0:nrOfTimeSteps]
Q_th_Last = Q_th_Last[0:nrOfTimeSteps]
p_el      = p_el     [0:nrOfTimeSteps]
aTimeSeries = aTimeSeries[0:nrOfTimeSteps]
        

##########################################################################

from flixStructure import *
from flixComps    import *
import logging as log
import os # für logging

root = logging.getLogger()
root.setLevel(os.environ.get("LOGLEVEL", "DEBUG"))
root.setLevel(os.environ.get("LOGLEVEL", "INFO"))
#log.basicConfig(level=logging.DEBUG)
log.warning('test warning')
log.info   ('test info')
log.debug  ('test debug')


print('#######################################################################')
print('################### start of modeling #################################')




# Bus-Definition:

# TODO: '''# Definition default Buses:
#     defaultBuses.el   = Strom;
#     defaultBuses.th   = Fernwaerme;
#     defaultBuses.fuel = Gas;'''

# Busse:
#                 Typ         Name              
Strom      = cBus('el'        ,'Strom'     );
Fernwaerme = cBus('th'        ,'Fernwärme' );  
Gas        = cBus('fuel'      ,'Gas'       );

# Effects
# TODO: einen Bus automatisch in cEffect erzeugen.
# TODO bei flow verhindern, dass der Effekt sich selber gleichen Effekt gibt
# TODO: für operational-box und invest-box: jeweils cFlow('allCosts', effBus_Costs) bauen -> dort kann man Grenzen einbauen

costs = cEffectType('costs','€'      , 'Kosten', isStandard = True, isObjective = True)
CO2   = cEffectType('CO2'  ,'kg'     , 'CO2_e-Emissionen', 
                    specificShareToOtherEffects_operation = {costs: 0.2}, 
                    specificShareToOtherEffects_invest    = {costs:1000}, 
                    )#max_Sum=3500, max_operationSum=3500, max_investSum=0.5)  


PE    = cEffectType('PE'   ,'kWh_PE' , 'Primärenergie'   )

# Komponentendefinition:

invest_Gaskessel = cInvestArgs(fixCosts = 1000,
                               investmentSize_is_fixed = True,
                               investment_is_optional=False,
                               specificCosts= {costs:10, PE:2},
                               min_investmentSize=0,
                               max_investmentSize=1000)
# invest_Gaskessel = None #
aGaskessel = cKessel('Kessel', eta = 0.5, costsPerRunningHour = {costs:0, CO2:1000},#, switchOnCosts = 0
                    Q_th = cFlow(label   = 'Q_th', 
                                 bus = Fernwaerme, 
                                 nominal_val = 50 , 
                                 loadFactor_max = 1.0, 
                                 loadFactor_min = 0.1,
                                 min_rel = 5/50, 
                                 max_rel = 1, 
                                 iCanSwitchOff = True, 
                                 onHours_min = 0, 
                                 onHours_max = 1000, 
                                 switchOnCosts = 0.01, 
                                 switchOn_maxNr = 1000, 
                                 valuesBeforeBegin=[50], 
                                 investArgs = invest_Gaskessel,
                                 sumFlowHours_max = 1e6,
                                 ),       # maxGradient = 5),
                    Q_fu = cFlow(label   = 'Q_fu', bus = Gas       , nominal_val = 200, min_rel = 0   , max_rel = 1)) 


aKWK  = cKWK('BHKW2', eta_th = 0.5, eta_el = 0.4, switchOnCosts =  0.01,
            P_el = cFlow('P_el',bus = Strom     , nominal_val = 60, min_rel = 5/60, ),
            Q_th = cFlow('Q_th',bus = Fernwaerme),
            Q_fu = cFlow('Q_fu',bus = Gas),on_valuesBeforeBegin = [1])


aKWK2 = cKWK('BHKW2', eta_th = 0.5, eta_el=0.4, switchOnCosts = 0.01,
            P_el = cFlow('P_el',bus = Strom     , nominal_val = 60, min_rel = 0),
            Q_th = cFlow('Q_th',bus = Fernwaerme),
            Q_fu = cFlow('Q_fu',bus = Gas),on_valuesBeforeBegin = [1])


aKWK2.setLinearSegments({aKWK2.P_el: [5  ,30, 40,60 ], # elemente können auch liste sein!
                         aKWK2.Q_th: [6  ,35, 45,100], 
                         aKWK2.Q_fu: [12 ,70, 90,200]})
# Anmerkung: Punkte über Segmentstart = Segmentende realisierbar, d.h. z.B. [4,4]

# segmentierte Kosten:
costsInvestsizeSegments = [[5,25,25,100], #kW
                           {costs:[50,250,250,800],#€
                            PE:[5,25,25,100] #kWh_PE
                            }
                           ]

# # alternative Angabe nur für Standardeffekt:
# costsInvestsizeSegments = [[5,25,25,100], #kW
#                             [50,250,250,800],#€
#                           ]

invest_Speicher = cInvestArgs(fixCosts = 0, 
                              investmentSize_is_fixed = False, 
                              costsInInvestsizeSegments = costsInvestsizeSegments, 
                              investment_is_optional=False, 
                              specificCosts= {costs: 0.01, CO2: 0.01}, 
                              min_investmentSize=0, max_investmentSize=1000)


aSpeicher = cStorage('Speicher',
                     inFlow  = cFlow('Q_th_load' , bus = Fernwaerme), 
                     outFlow = cFlow('Q_th_unload',bus = Fernwaerme), 
                     # capacity_inFlowHours = 30, 
                     capacity_inFlowHours = None, 
                     chargeState0_inFlowHours = 0, 
                     # charge_state_end_min = 3
                     charge_state_end_max = 10, 
                     eta_load = 0.9, eta_unload = 1, 
                     fracLossPerHour = 0.08, 
                     avoidInAndOutAtOnce= True,
                     investArgs = invest_Speicher)
 
aWaermeLast       = cSink  ('Wärmelast',sink   = cFlow('Q_th_Last' , bus = Fernwaerme, nominal_val = 1, min_rel = 0, val_rel = Q_th_Last))

aGasTarif         = cSource('Gastarif' ,source = cFlow('Q_Gas'     , bus = Gas  , nominal_val = 1000, costsPerFlowHour= {costs: 0.04, CO2: 0.3}))

# aStromEinspeisung = cSink  ('Einspeisung'    ,sink   = cFlow('P_el'      , bus = Strom, costsPerFlowHour = -0.07*10))
aStromEinspeisung = cSink  ('Einspeisung'    ,sink   = cFlow('P_el'      , bus = Strom, costsPerFlowHour = -p_el))

# Zusammenführung:
es = cEnergySystem(aTimeSeries, dt_last=None)
# es.addComponents(aGaskessel,aWaermeLast,aGasTarif)#,aGaskessel2)
es.addEffects(costs, CO2, PE)
es.addComponents(aGaskessel, aWaermeLast, aGasTarif)
es.addComponents(aStromEinspeisung)
es.addComponents(aKWK)

es.addComponents(aSpeicher)

# flix.mainSystem.extractSubSystem([0,1,2])

chosenEsTimeIndexe = None
# chosenEsTimeIndexe = [1,3,5]

## geschlossene Modellierung:

aCalc = cCalculation('Sim1', es, 'pyomo', chosenEsTimeIndexe)
aCalc.doModelingAsOneSegment()

# PRINT Model-Charactaricstics:
es.printModel()
es.printVariables()
es.printEquations()

solverProps = {'gapFrac': gapFrac, 
               'timelimit': timelimit,
               'solver': solver_name, 
               'displaySolverOutput' : displaySolverOutput,
               'threads': nrOfThreads} # nur gurobi!

## geschlossene Berechnung:

aCalc.solve(solverProps, nameSuffix = '_' + solver_name)

aCalc.results_struct

## segmentierte Berechnung:

if doSegmentedCalc: 
  calcSegs = cCalculation('Sim2', es, 'pyomo', chosenEsTimeIndexe)
  calcSegs.doSegmentedModelingAndSolving(solverProps, segmentLen = 6, nrOfUsedSteps = 2, nameSuffix = '_' + solver_name)
 

## segmentiertes Plotting -> todo -> Umzug in Postprocesing!!!

if doSegmentedCalc: 
  import matplotlib.pyplot as plt
  # Segment-Plot:
  for aModBox in calcSegs.segmentModBoxList:  
    plt.plot(aModBox.timeSeries       , aModBox.results_struct.BHKW2.Q_th.val, label='Q_th_BHKW') 
  plt.plot(calcSegs.timeSeries       , calcSegs.results_struct.BHKW2.Q_th.val, label='Q_th_BHKW') 
  # plt.plot(calcSegs.timeSeriesWithEnd, calcSegs.results_struct.Speicher.charge_state, ':', label='chargeState') 
  # plt.plot(mb      .timeSeriesWithEnd, mb      .results_struct.Speicher.charge_state, '-.', label='chargeState') 
  plt.legend()
  plt.grid()
  plt.show()
  

  # Segment-Plot:
  for aModBox in calcSegs.segmentModBoxList:  
    plt.plot(aModBox.timeSeries, aModBox.results_struct.globalComp.costs.operation.sum_TS, label='costs') 
  plt.plot(calcSegs.timeSeries       , calcSegs.results_struct.globalComp.costs.operation.sum_TS, ':', label='costs') 
  plt.legend()
  plt.grid()
  plt.show()
  
  calcSegs.results_struct


## TESTING: ##
print('#############')
print('## Testing ##')  
if solver_name == 'cbc':
  assert round(aCalc.listOfModbox[0].objective_value) == -11728,'!!!Achtung Ergebnis-Änderung!!!'
else: # gurobi
  assert round(aCalc.listOfModbox[0].objective_value,-1) == -10760,'!!!Achtung Ergebnis-Änderung!!!'
print('##   ok!   ##')
print('#############')

if doSegmentedCalc: 
  assert round(0.001* sum(calcSegs.results_struct.globalComp.costs.operation.sum_TS )) == -12, 'TESTING segmentweise - Achtung: Ergebnisse stimmen nicht mehr!'
