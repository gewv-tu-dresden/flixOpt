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
Q_th_Last = [0, 10, 100]
# aTimeSeries = pd.date_range('1/1/2020',periods=len(Q_th_Last),freq='1H')
aTimeSeries = [datetime.datetime(2020, 1,1)] +  np.arange(len(Q_th_Last)) * datetime.timedelta(hours=1)
aTimeSeries = aTimeSeries.astype('datetime64')
    
##########################################################################


class mySystem():

  def __init__(self, label, investArgs, penaltyCosts = 1e5, Q_th_nominal = 150, min_rel = 0.1):
    self.label = label
    # Effects
    costs = cEffectType('costs','€'      , 'Kosten', isStandard = True, isObjective = True)
    CO2   = cEffectType('CO2'  ,'kg'     , 'CO2_e-Emissionen', 
                        specificShareToOtherEffects_operation = {costs: 0.2}, 
                        specificShareToOtherEffects_invest    = {costs:1000}, 
                        )
      
    self.costs = costs
    self.CO2 = CO2
    
    # Busse:
    Strom      = cBus('el'        ,'Strom'     );
    Heat       = cBus('th'        ,'heat' ,excessCostsPerFlowHour = penaltyCosts,);  
    Gas        = cBus('fuel'      ,'Gas'       );
    self.Strom = Strom
    self.Heat  = Heat
    self.Gas   = Gas
     
    aGaskessel = cKessel('Kessel', eta  = 0.4, costsPerRunningHour = {costs:0, CO2:1000},#, switchOnCosts = 0
                        Q_th = cFlow(label   = 'Q_th', bus = Heat, nominal_val = Q_th_nominal , min_rel = min_rel, switchOnCosts=0.01, investArgs = investArgs),       # maxGradient = 5),
                        Q_fu = cFlow(label   = 'Q_fu', bus = Gas , min_rel = 0)) 

    self.Kessel = aGaskessel    
    aWaermeLast = cSink  ('Wärmelast',sink   = cFlow('Q_th_Last' , bus = Heat, nominal_val = 1, min_rel = 0, val_rel = Q_th_Last))  
    aGasTarif   = cSource('Gastarif' ,source = cFlow('Q_Gas'     , bus = Gas , nominal_val = 1000, costsPerFlowHour= {costs: 0.04, CO2: 0.3}))
        
    # Zusammenführung:
    self.es = cEnergySystem(aTimeSeries)
    self.es.addEffects(costs, CO2)
    self.es.addComponents(aGaskessel)
    self.es.addComponents(aWaermeLast, aGasTarif)
    # flix.addComponents(aGaskessel2)
    
  
  def modelAndSolve(self):
    aCalc = cCalculation('Sim1',self.es,'pyomo')
    aCalc.doModelingAsOneSegment()
    self.es.printModel()
    self.es.printVariables()
    self.es.printEquations()
    solverProps = {'gapFrac': gapFrac, 
                   'solver': solver_name, 
                   'displaySolverOutput' : displaySolverOutput,
                   }
    
    ## geschlossene Berechnung:  
    aCalc.solve(solverProps, saveResults=False)
    self.calc = aCalc
    return aCalc.results_struct
  
  def print(self):
    print('### ' + self.label + ' ###')
    aCalc = self.calc
    print('Kessel_nominal_val : ' + str(aCalc.results_struct.Kessel.Q_th.invest.nominal_val))
    print('costs_invest       : ' + str(aCalc.results_struct.globalComp.costs.invest.sum) + ' €')
    print('Bedarf.Q_th        : ' + str(aCalc.results_struct.Waermelast.Q_th_Last.val))
    print('kessel.Q_th        : ' + str(aCalc.results_struct.Kessel.Q_th.val))
    print('heat.exzess        : ' + str(aCalc.results_struct.heat.excessIn - aCalc.results_struct.heat.excessOut))    
    if hasattr(aCalc.results_struct.Kessel.Q_th.invest, 'isInvested'):
        print('isInvested         : ' + str(aCalc.results_struct.Kessel.Q_th.invest.isInvested))    




# Test1: #
# -> feste Investgröße, 
# -> invest zwingend
investArgs = cInvestArgs(fixCosts = 1e3,
                            investmentSize_is_fixed = True, 
                            investment_is_optional = False,
                            specificCosts = 10)

test1 = mySystem('test1',investArgs, penaltyCosts = 1e5, Q_th_nominal = 150)
struct = test1.modelAndSolve()
test1.print()
assert (struct.Kessel.Q_th.invest.nominal_val == 150 and # fixer Nennwert
        np.array_equal(struct.Kessel.Q_th.val, [0, 15, 100]) and # Lastgang abgefahren, aber > minimum
        struct.globalComp.costs.invest.sum == 150 * 10 + 1e3) # Kosten


        
# Test2: #
# -> feste Investgröße, 
# -> optionale Invest 
# -> (penalty = klein, damit ist Invest nicht notwendig)
investArgs = cInvestArgs(fixCosts = 1e3,
                          investmentSize_is_fixed = True, 
                          investment_is_optional = True,
                          specificCosts = 10)

test2 = mySystem('test1',investArgs, penaltyCosts = 0.1, Q_th_nominal = 150)
struct = test2.modelAndSolve()
test2.print()
assert (struct.Kessel.Q_th.invest.isInvested == 0 and
        struct.globalComp.costs.invest.sum == 0)


# Test3: #
# -> VARIABLE Investgröße, 
# -> invest zwingend 
investArgs = cInvestArgs(fixCosts = 1e3,
                          investmentSize_is_fixed = False, 
                          investment_is_optional = False,
                          specificCosts = 10,
                          min_investmentSize=0,
                          max_investmentSize=2000)

test3 = mySystem('test1',investArgs, penaltyCosts = 1e5, Q_th_nominal = None)
struct = test3.modelAndSolve()
test3.print()
assert (struct.Kessel.Q_th.invest.nominal_val == 100 and
        struct.globalComp.costs.invest.sum == 2000) # 100 * 10 + 1000

# Test3a): #
# -> VARIABLE Investgröße, 
# -> invest zwingend 
# -> Kessel-Min_Rel ist 0.15
investArgs = cInvestArgs(fixCosts = 1e3,
                          investmentSize_is_fixed = False, 
                          investment_is_optional = False,
                          specificCosts = 10,
                          min_investmentSize=0,
                          max_investmentSize=2000)

test3 = mySystem('test1',investArgs, penaltyCosts = 1e5, Q_th_nominal = None, min_rel = 0.15)
struct = test3.modelAndSolve()
test3.print()
assert (struct.Kessel.Q_th.invest.nominal_val == 100 and
        struct.globalComp.costs.invest.sum == 2000 and # 100 * 10 + 1000
        np.array_equal(struct.Kessel.Q_th.val, [0, 15, 100])) # Lastgang abgefahren, aber > minimum

# Test3b): #
# --> Nominalwert fälschlicherweise mit Wert belegt.
try:
  test3 = mySystem('test1',investArgs, penaltyCosts = 1e5, Q_th_nominal = 150, min_rel = 0.15)                
except:
  pass # es sollte ein Fehler kommen
else: # wenn KEIN Fehler
  raise Exception('Test nicht gültig') #