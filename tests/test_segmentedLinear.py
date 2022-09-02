# -*- coding: utf-8 -*-
"""
Created on Thu Jun 16 11:19:17 2022

@author: Panitz
"""


# mögliche Testszenarien für testing-tool:
   # abschnittsweise linear testen
   # Komponenten mit offenen Flows 
   # Binärvariablen ohne max-Wert-Vorgabe des Flows (Binärungenauigkeitsproblem)
   # Medien-zulässigkeit 
   

### Inputs: ####
# Solver-Inputs:
gapFrac        = 0.02
timelimit      = 3600
solver_name    = 'gurobi'

import numpy as np
import datetime

    
####################### kleine Daten zum Test ###############################
Q_th_Last = np.arange(0,150,1)
   
# todo: ggf. Umstellung auf numpy: aTimeSeries = datetime.datetime(2020, 1,1) +  np.arange(len(Q_th_Last)) * datetime.timedelta(hours=1)
aTimeSeries = datetime.datetime(2020, 1,1) +  np.arange(len(Q_th_Last)) * datetime.timedelta(hours=1)
aTimeSeries = aTimeSeries.astype('datetime64')

##########################################################################

from flixStructure import *
from flixComps    import *

print('#######################################################################')
print('################### start of modeling #################################')


# Busse:
#                 Typ         Name              
Strom      = cBus('el'        ,'Strom'     );
Fernwaerme = cBus('th'        ,'Fernwärme' );  
Gas        = cBus('fuel'      ,'Gas'       );

costs = cEffectType('costs','€'      , 'Kosten', isStandard = True, isObjective = True)


# invest_Gaskessel = None #
teurerGaskessel = cKessel('Kessel', eta  = 0.5, 
                    Q_th = cFlow(label   = 'Q_th', 
                                 bus = Fernwaerme, 
                                 costsPerFlowHour = 10
                                 ),
                    Q_fu = cFlow(label   = 'Q_fu', bus = Gas))




aKWK  = cKWK('BHKW', eta_th = 0.5, eta_el = 0.4, switchOnCosts =  0.01,
            P_el = cFlow('P_el',bus = Strom     ),
            Q_th = cFlow('Q_th',bus = Fernwaerme),
            Q_fu = cFlow('Q_fu',bus = Gas))

#                                    seg,    seg,   point , seg
aKWK.setLinearSegments({aKWK.P_el:  [5  ,30, 40,60, 70, 70, 80, 65 ], 
                         aKWK.Q_th: [6  ,35, 45,100, 110, 110, 120, 130  ],
                         aKWK.Q_fu: [12 ,70, 90,200, 220, 220, 230, 260]})

aWaermeLast       = cSink  ('Wärmelast',sink   = cFlow('Q_th_Last', bus = Fernwaerme, val_rel = Q_th_Last, nominal_val=1))

aGasTarif         = cSource('Gastarif', source = cFlow('Q_Gas', bus = Gas))

aStromEinspeisung = cSink  ('Einspeisung',sink   = cFlow('P_el', bus = Strom))

# Zusammenführung:
es = cEnergySystem(aTimeSeries)
es.addEffects(costs)
es.addComponents(teurerGaskessel, aWaermeLast, aGasTarif, aStromEinspeisung, aKWK)

aCalc = cCalculation('Sim1', es, 'pyomo')
aCalc.doModelingAsOneSegment()

solverProps = {'solver': solver_name,
               'displaySolverOutput':False} # nur gurobi!

aCalc.solve(solverProps, nameSuffix = '_' + solver_name, saveResults = False)

# Plotting: #

import matplotlib.pyplot as plt

plt.scatter(aCalc.results_struct.BHKW.Q_fu.val, aCalc.results_struct.BHKW.Q_th.val,marker='.')
plt.scatter(aCalc.results_struct.BHKW.Q_fu.val, aCalc.results_struct.BHKW.P_el.val,marker='.')
plt.show()


# Testing #
soll = np.array([  0.,   0.,   0.,   0.,   0.,   0.,  12.,  14.,  16.,  18.,  20.,
        22.,  24.,  26.,  28.,  30.,  32.,  34.,  36.,  38.,  40.,  42.,
        44.,  46.,  48.,  50.,  52.,  54.,  56.,  58.,  60.,  62.,  64.,
        66.,  68.,  70.,  70.,  70.,  70.,  70.,  70.,  70.,  70.,  70.,
        70.,  90.,  92.,  94.,  96.,  98., 100., 102., 104., 106., 108.,
       110., 112., 114., 116., 118., 120., 122., 124., 126., 128., 130.,
       132., 134., 136., 138., 140., 142., 144., 146., 148., 150., 152.,
       154., 156., 158., 160., 162., 164., 166., 168., 170., 172., 174.,
       176., 178., 180., 182., 184., 186., 188., 190., 192., 194., 196.,
       198., 200., 200., 200., 200., 200., 200., 200., 200., 200., 200.,
       220., 220., 220., 220., 220., 220., 220., 220., 220., 220., 230.,
       233., 236., 239., 242., 245., 248., 251., 254., 257., 260., 260.,
       260., 260., 260., 260., 260., 260., 260., 260., 260., 260., 260.,
       260., 260., 260., 260., 260., 260., 260.])

if np.all( np.around(soll,2) == np.around(aCalc.results_struct.BHKW.Q_fu.val,2)):
  print('### segmentedLinear Test ok ###')
else:
  raise Exception('## segmentedLinear Test NICHT ok ##')