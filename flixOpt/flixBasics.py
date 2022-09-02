# -*- coding: utf-8 -*-
"""
Created on Wed Mar 31 22:51:38 2021

@author: Panitz
"""

import numpy as np
import flixOptHelperFcts as helpers

# stellt Infrastruktur printInitArgs() etc zur Verfügung:
# gibt Warnung, falls unbenutzte kwargs vorhanden!
class cArgsClass:
  
  # diese Klassen-Methode holt aus dieser und den Kindklassen alle zulässigen Argumente der Kindklasse! 
  @classmethod
  def printInitArgs(cls):
    print('init-args of ' + cls.__name__ + ':')
    listOfInitArgs = cls.getInitArgs()
    for aProp in listOfInitArgs:
      aProp.print('  ')
      
  @classmethod  
  def getInitArgs(cls):        

    ### 1. Argumente der Mutterklasse (rekursiv) ###
    # wird rekursiv aufgerufen bis man bei Mutter-Klasse cModelingElement ankommt.
    # nur bis zu cArgsClass zurück gehen:
    if hasattr(cls.__base__,'getInitArgs'):#man könnte auch schreiben: if cls.__name__ == cArgsClass  
      allArgsFromMotherClass = cls.__base__.getInitArgs()  # rekursiv in Mutterklasse aufrufen
    
    # wenn cls.__base__ also bereits eine Ebene UNTER cArgsClass:
    else:
      allArgsFromMotherClass = []    
    
    # checken, dass die zwei class-Atributes auch wirklich für jede Klasse (und nicht nur für Mutterklasse) existieren (-> die nimmt er sonst einfach automatisch)
    if (not ('not_used_args' in cls.__dict__)) | (not ('new_init_args' in cls.__dict__)):
      raise Exception('class ' + cls.__name__ + ': you forgot to implement class attribute <not_used_args> or/and <new_int_args>')
    notTransferedMotherArgs = cls.not_used_args    

    ### 2. Abziehen der nicht durchgereichten Argumente ###
    # delete not Transfered Args:
    allArgsFromMotherClass = [prop for prop in allArgsFromMotherClass if prop.label not in notTransferedMotherArgs]
       
    
    ### 3. Ergänzen der neuen Argumente ###
    myArgs =  cls.new_init_args.copy() # get all new arguments of __init__() (as a copy)
    # melt lists:
    myArgs.extend(allArgsFromMotherClass)
    return myArgs
    
  # Diese Variablen muss jede Kindklasse auch haben:
  new_init_args = []
  not_used_args = [] 
  
  def __init__(self, **kwargs):
    # wenn hier kwargs auftauchen, dann wurde zuviel übergeben:
    if len(kwargs) > 0 :
      raise Exception('class and its motherclasses have no allowed arguments for:' + str(kwargs)[:200])
      
# Definiert Input/Argument/Eigenschaft für Komponenten/Flows
class cArg:
  def __init__(self, label, propType, dType, description):
    self.label        = label
#     self.defaultValue = defaultValue
    self.dType        = dType    
    self.description  = description
    self.propType     = propType # costs, params, initValues
    
  def print(self, prefixChars):    
    print(prefixChars + self.label + ' : ' + self.propType + ' | ' + str(self.dType) + ' | ' + self.description )      
    
    
# Klasse für Timeseries-Vektoren bzw. Skalare, die für Zeitreihe gelten
class cTS_vector:  
  # create and register in List:

  # gets rawdata only of activated esIndexe:
  @property
  def d_i_raw(self):
    if (np.isscalar(self.d)) or (self.d is None) or (self.__timeIndexe_actual is None):
      return self.d
    else:
      return self.d[self.__timeIndexe_actual]
  
  # Vektor:
  @property  
  def d_i_raw_vec(self):    
    vec = helpers.getVector(self.d_i_raw, len(self.__timeIndexe_actual))
    return vec
  
  @property
  # gets data only of activated esIndexe or explicit data::
  def d_i(self):
    # wenn d_i_explicit gesetzt wurde:
    if self.d_i_explicit is not None:
      return self.d_i_explicit
    else:
      return self.d_i_raw


  @property
  def isscalar(self):
    return np.isscalar(self.d)
  @property 
  def isArray(self):
    return (not(self.isscalar)) & (not(self.d is None))

  @property
  def label_full(self):
    return self.owner.label_full + '_' + self.label    
    
        
  def __init__(self, label, value, owner):    
    self.label  = label
    self.owner = owner
    
    self.d = self.__makeSkalarIfPossible(value) # (d wie data), d so knapp wie möglich speichern
    self.d_i_explicit = None #     
    
    self.__timeIndexe_actual = None # aktuelle timeIndexe der modBox
    
    owner.TS_list.append(self)    

  @staticmethod
  def __makeSkalarIfPossible(d):        
    if (np.isscalar(d)) or (d is None):
      # do nothing
      pass
    else :
      d = np.array(d) # Umwandeln, da einfaches slicing mit Index-Listen nur mit np-Array geht.     
      # Wenn alle Werte gleich, dann Vektor in Skalar umwandeln:
      if np.all(d == d[0]):        
        d = d[0]
    return d
      

  # define, which timeStep-Set should be transfered in data-request self.d_i()    
  def activate(self, dataTimeIndexe, d_i_explicit = None):
    # time-Index:  
    self.__timeIndexe_actual = dataTimeIndexe

    # explicitData:    
    if d_i_explicit is not None:
      assert ((len(d_i_explicit) == len(self.__timeIndexe_actual)) or \
             (len(d_i_explicit) == 1 )) , 'd_i_explicit has not right length!'
             
    self.d_i_explicit = self.__makeSkalarIfPossible(d_i_explicit)

  
  # Rückgabe Maximum
  def max(self):
    return cTS_vector.__getMax(self.d)    
  
  # Maximum für indexe:
  def max_i(self):
    return cTS_vector.__getMax(self.d_i)    
  
  def __getMax(aValue):
    if np.isscalar(aValue):
      return aValue
    else:
      return max(aValue)


# if costs is given without effectType, standardeffect is related
  # costs = {20}                      -> {None:20}
  # costs = None                      -> no change
  # costs = {effect1:20, effect2:0.3} -> no change  
def getEffectDictOfEffectValues(effect_values):
    ## Umwandlung in dict:
    # Wenn schon dict:
    if isinstance(effect_values, dict):
      # nur übergeben, nix machen
      effect_values_dict = effect_values
    elif effect_values is None:
      effect_values_dict = None   
    # Wenn Skalar oder TS:
    else:
      # dict bauen mit standard-effect:
      effect_values_dict = {None: effect_values}  # standardType noch nicht bekannt, dann None. Wird später Standard-Effekt-Type

    return effect_values_dict



# macht alle Effekt-Wert-dicts, aus Wert cTS_vector 
def transformDictValuesToTS(nameOfParam, aDict, owner):
  # Einzelne Faktoren zu Vektoren: 
  aDict_TS = {}#
  # für jedes Dict -> Values (=Faktoren) zu Vektoren umwandeln:         
  if aDict is None:
    aDict_TS = None
  else:
    for key, value in aDict.items():
      if not isinstance(value, cTS_vector):
        # Subnamen aus key:
        if key is None:
          subname = 'standard' # Standard-Effekt o.ä. # todo: das ist nicht schön, weil costs in Namen nicht auftaucht
        else:
          subname = key.label # z.B. costs, Q_th,...
        nameOfParam_full   = nameOfParam + '_' + subname # name ergänzen mit key.label
        aDict_TS[key] = cTS_vector(nameOfParam_full, value, owner) # Transform to TS    
    return aDict_TS
  
# Transforms effect/cost-input to dict of TS, 
#   wenn nur wert gegeben, dann wird gegebener effect zugeordnet
#   effectToUseIfOnlyValue = None -> Standard-EffektType wird genommen
# Fall 1:
#     output = {effect1 : TS1, effects2: TS2}
# Fall2 (falls Skalar übergeben):
#     output = {standardEffect : TS1}
def transFormEffectValuesToTSDict(nameOfParam, aEffectsValue, ownerOfParam):  

    # add standardeffect if only value is given:
    effectsDict = getEffectDictOfEffectValues(aEffectsValue)
    # dict-values zu cTS_vectoren:  
    effectsDict_TS = transformDictValuesToTS(nameOfParam, effectsDict, ownerOfParam)  
    return effectsDict_TS