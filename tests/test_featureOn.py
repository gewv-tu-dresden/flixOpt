# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 10:45:34 2022

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
   

### Inputs: ####
# Solver-Inputs:
displaySolverOutput = False # ausführlicher Solver-Output.
gapFrac        = 0.02
solver_name    = 'gurobi'
solver_name    = 'cbc'
################

import matplotlib.pyplot as plt
import numpy as np
from flixStructure import *
from flixComps    import *
import datetime
  
####################### kleine Daten zum Test ###############################
Q_th_Last = [5, 0, 5, 10, 10, 0, 15]
aTimeSeries = [datetime.datetime(2020, 1,1)] +  np.arange(7) * datetime.timedelta(hours=0.5)
aTimeSeries = aTimeSeries.astype('datetime64')

        
##########################################################################


class mySystem():

  def __init__(self, label, Q_th_Last, penaltyCosts = 1e5, switchOnCosts = None, investArgs = None, switchOn_maxNr_K1 = None, switchOn_maxNr_K2 = None, onHoursSum_max_K1 = None, onHoursSum_max_K2 = None):
    self.label = label
    # Effects
    costs = cEffectType('costs','€'      , 'Kosten', isStandard = True, isObjective = True)
    CO2   = cEffectType('CO2'  ,'kg'     , 'CO2_e-Emissionen', 
                        specificShareToOtherEffects_operation = {costs: 0.2}, 
                        specificShareToOtherEffects_invest    = {costs:1000}, 
                        )
      
    self.costs = costs
    
    # Busse:
    Heat       = cBus('th'        ,'heat' ,excessCostsPerFlowHour = penaltyCosts,);  
    Gas        = cBus('fuel'      ,'Gas'       );
    self.Heat = Heat
    self.Gas  = Gas
     
    # guter Kessel:
    self.K1 = cKessel('Kessel1', eta  = 0.5, costsPerRunningHour = 0,
                        Q_th = cFlow(label   = 'Q_th', bus = Heat, nominal_val = 10 , switchOnCosts=switchOnCosts, switchOn_maxNr = switchOn_maxNr_K1, onHoursSum_max = onHoursSum_max_K1, investArgs = investArgs),
                        Q_fu = cFlow(label   = 'Q_fu', bus = Gas)) 
    # schlechter Kessel
    self.K2 = cKessel('Kessel2', eta  = 0.4, costsPerRunningHour = 0,
                        Q_th = cFlow(label   = 'Q_th', bus = Heat, nominal_val = 10 , switchOnCosts=switchOnCosts, switchOn_maxNr = switchOn_maxNr_K2, onHoursSum_max = onHoursSum_max_K2, investArgs = investArgs),
                        Q_fu = cFlow(label   = 'Q_fu', bus = Gas))

    aWaermeLast = cSink  ('Wärmelast',sink   = cFlow('Q_th_Last' , bus = Heat, val_rel = Q_th_Last, nominal_val = 1))  
    aGasTarif   = cSource('Gastarif' ,source = cFlow('Q_Gas'     , bus = Gas , costsPerFlowHour= 0.04))    
        
    # Zusammenführung:
    self.es = cEnergySystem(aTimeSeries)
    self.es.addEffects(costs, CO2)
    self.es.addComponents(self.K1, self.K2)
    self.es.addComponents(aWaermeLast, aGasTarif)
      
  def modelAndSolve(self):

    self.calc = cCalculation('calc1', self.es, 'pyomo')
    self.calc.doModelingAsOneSegment()
    self.es.printModel()
    self.es.printVariables()
    self.es.printEquations()
    solverProps = {'gapFrac': gapFrac, 
                   'solver': solver_name, 
                   'displaySolverOutput' : displaySolverOutput,
                   } # nur gurobi!
    
    

    ## geschlossene Berechnung:  
    self.calc.solve(solverProps, saveResults = False)
    # uebersichtsPlot(mb)
    
    return self.calc.results_struct
  
  def print(self):
    print('### ' + self.label + ' ###')
    aCalc = self.calc
    try: 
      print('K1 Starts: ' + str(aCalc.results_struct.Kessel1.Q_th.nrSwitchOn)) 
    except: 
        pass
    try: 
      print('K2 Starts: ' + str(aCalc.results_struct.Kessel2.Q_th.nrSwitchOn)) 
    except: 
      pass
    print('K1 onHoursSum: ' + str(aCalc.results_struct.Kessel1.Q_th.onHoursSum))
    print('K2 onHoursSum: ' + str(aCalc.results_struct.Kessel2.Q_th.onHoursSum))


# Test1a: #
# -> switchOn_maxNr
Q_th_Last = [5, 0, 5, 10, 10, 0, 15]
test1 = mySystem('test1', Q_th_Last, switchOn_maxNr_K1 =1, switchOn_maxNr_K2 = 10)
struct = test1.modelAndSolve()
test1.print()
assert ((struct.Kessel1.Q_th.nrSwitchOn == 1) and
       (struct.Kessel2.Q_th.nrSwitchOn == 3)), 'Test nicht erfolgreich'

# Test1b: #
# -> switchOn_maxNr
test1b = mySystem('test1b', Q_th_Last, switchOn_maxNr_K1 = 0, switchOn_maxNr_K2 = 10)
struct = test1b.modelAndSolve()
test1b.print()
assert ((struct.Kessel1.Q_th.nrSwitchOn == 0) and
       (struct.Kessel2.Q_th.nrSwitchOn == 3)), 'Test nicht erfolgreich'

# Test2: #
# -> onHoursSum
test2 = mySystem('test2', Q_th_Last, onHoursSum_max_K1 = 0.5, onHoursSum_max_K2 = 20)
struct = test2.modelAndSolve()
test2.print()
assert ((struct.Kessel1.Q_th.onHoursSum == 0.5) and
       (struct.Kessel2.Q_th.onHoursSum == 2.5)), 'Test nicht erfolgreich'