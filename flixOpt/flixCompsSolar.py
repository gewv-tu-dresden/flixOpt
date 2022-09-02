# -*- coding: utf-8 -*-
"""
Created on Mon May 23 12:09:40 2022

@author: Panitz
"""

import numpy  as np


import flixOptHelperFcts as helpers

from basicModeling import * # Modelliersprache
from flixStructure  import * # Grundstruktur
from flixFeatures   import *


  investSolar = cInvestArgs(fixCosts=0,
                            # investmentSize_is_fixed=False, 
                            investmentSize_is_fixed=False, 
                            investment_is_optional=True, 
                            specificCosts={costs: 250 / years, area:solar.A_Verhaeltnis},#€/m² | m²_Grund/m²_K
                            min_investmentSize=20, # m²_K
                            max_investmentSize=20000, # m²_K# eigtl durch area bereit begrenzt
                               )
  
  sourceFlow = cFlow('Q_th_sol',
                     bus = Fernwaerme,
                     nominal_val = None,
                     # nominal_val = 1000, # m²_K                     
      #               min_rel = 0, -> Verwendung bei Rücklaufbeimischung zur Stagnationsverhinderung
      #               max_rel = ,
                     val_rel = solar.Last_spez, # kW/m²
                     investArgs = investSolar,
                     )
  

class Solarthermal(cSource):
  
  
  
  
  
  new_init_args = [cArg('source'              , 'flow',  'flow',  'flow-output Quelle')]        
  
  
  ''' 
  tilt
  azimut
  ...
  
  throttlingIsPossible -> max_rel statt val_rel
  
  
  '''
  
  
  
  def __init__(self, label, bus, nominal_val = None, investSolar = None, **kwargs):
    self.source = cFlow('Q_th_sol',                      
                        nominal_val = nominal_val,
          #               min_rel = 0, -> Verwendung bei Rücklaufbeimischung zur Stagnationsverhinderung
          #               max_rel = ,
                        val_rel = solar.Last_spez, # kW/m²
                        investArgs = investSolar,
                         )
    super().__init__(label, source, **kwargs)
    self.source = source
    self.outputs.append(source) # ein Output-Flow      
    


class PV(cSource):    