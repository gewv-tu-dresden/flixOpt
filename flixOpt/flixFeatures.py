# -*- coding: utf-8 -*-
"""
Created on Thu Mar 18 18:43:55 2021

@author: Panitz
"""
## TODO:
  
  # featureAvoidFlowsAtOnce:
    # neue Variante (typ="new") austesten
      
from flixStructure  import * # Grundstruktur

##############################################################  
## Funktionalität/Features zum Anhängen an die Komponenten: ##  

class cFeature(cME):
  
  def __init__(self, label, owner, **kwargs):
    self.owner = owner
    if not self in self.owner.subElements:
      self.owner.subElements.append(self) # register in owner    
    super().__init__(label, **kwargs)
  
  @property
  def label_full(self):
    return self.owner.label_full + '.' + self.label 

  def finalize(self): # TODO: evtl. besser bei cME aufgehoben
    super().finalize()
  
# Abschnittsweise linear:
class cFeatureLinearSegmentVars(cFeature) : 
  # TODO: beser wäre hier schon Übergabe segmentsOfVars, aber schwierig, weil diese hier noch nicht vorhanden sind!
  def __init__(self, label, owner):   
    super().__init__(label, owner)
  

  # segements separat erst jetzt definieren, damit Variablen schon erstellt sind.
  # todo: wenn cVariable-Dummys existieren, dann kann das alles in __init__
  def defineSegments(self, segmentsOfVars, var_on, checkListOfVars):
    # segementsData - Elemente sind Listen!.
    # segmentsOfVars = {var_Q_fu: [ 5  , 10,  10, 22], # je zwei Werte bilden ein Segment. Indexspezfika (z.B. für Zeitreihenabbildung) über arrays oder TS!!
    #                   var_P_el: [ 2  , 5,    5, 8 ],
    #                   var_Q_th: [ 2.5, 4,    4, 12]}
        
    # -> onVariable ist optional
    # -> auch einzelne zulässige Punkte können über Segment ausgedrückt werden, z.B. [5, 5]

    self.segmentsOfVars = segmentsOfVars
    self.var_on = var_on
    
    # Anzahl Segmente bestimmen:      
    segmentDataOfFirstVariable = next(iter(segmentsOfVars.values()))
    nrOfColumns = len(segmentDataOfFirstVariable) # Anzahl Spalten
    self.nrOfSegments = nrOfColumns / 2 # Anzahl der Spalten der Matrix / 2 = Anzahl der Segmente  
    
    # Check ob gerade Anzahl an Werten:
    if not self.nrOfSegments.is_integer() : 
      raise Exception('Nr of Values should be even, because pairs (start,end of every section)')
        
    # Check, ob alle Variables vorhanden:
    if checkListOfVars is not None:
      setOfVars = set(segmentsOfVars.keys())
      toMuchSet = setOfVars - set(checkListOfVars) 
      missingSet = set(checkListOfVars) - setOfVars
      # Wenn Unterschiede vorhanden:
      def getStrOfSet(aSet):
        aStr = []
        for aVar in aSet:
          aStr += ',' + aVar.label_full
        return aStr
      # überflüssige Flows: 
      if toMuchSet :
        raise Exception('segmentsOfVars-Definition has not necessary vars: ' + getStrOfSet(toMuchSet))
      # fehlende Flows:
      if missingSet:
        raise Exception('segmentsOfVars miss following vars: ' + getStrOfSet(missingSet))
    # Aufteilen der Daten in die Segmente:
    self.listOfSegments = []   
    for aSecNr in range(int(self.nrOfSegments)):           

      # samplePoints für das Segment extrahieren:
      # z.B.   {var1:[TS1.1, TS1.2]
      #         var2:[TS2.1, TS2.2]}            
      samplePointsOfSegment = cFeatureLinearSegmentVars.__extractSamplePoints4Segment(segmentsOfVars, aSecNr)
      # Segment erstellen und in Liste::
      newSegment = cSegment('seg_' + str(aSecNr), self, samplePointsOfSegment, aSecNr)
      
      # todo: hier muss activate() selbst gesetzt werden, weil bereits gesetzt 
      # todo: alle cMEs sollten eigentlich hier schon längst instanziert sein und werden dann auch activated!!!
      newSegment.createNewModAndActivateModBox(self.modBox)
      self.listOfSegments.append(newSegment)
       
  def declareVarsAndEqs(self, modBox:cModelBoxOfES):
    for aSegment in self.listOfSegments :
      # Segmentvariablen erstellen:
      aSegment.declareVarsAndEqs(modBox)
  
  def doModeling(self,modBox:cModelBoxOfES,timeIndexe):                 
    #########################################
    ## 1. Gleichungen für: Nur ein Segment kann aktiv sein! ##
    # eq: -On(t) + Segment1.onSeg(t) + Segment2.onSeg(t) + ... = 0 
    # -> Wenn Variable On(t) nicht existiert, dann nur 
    # eq:          Segment1.onSeg(t) + Segment2.onSeg(t) + ... = 1                                         
    
    self.eq_IcanOnlyBeInOneSegment = cEquation('ICanOnlyBeInOneSegment', self, modBox)    
    
    # a) zusätzlich zu Aufenthalt in Segmenten kann alles auch Null sein:
    if (self.var_on is not None) and (self.var_on is not None) :   # Eigentlich wird die On-Variable durch linearSegment-equations bereits vollständig definiert.      
      self.eq_IcanOnlyBeInOneSegment.addSummand(self.var_on, -1);
    # b) Aufenthalt nur in Segmenten erlaubt:
    else :
      self.eq_IcanOnlyBeInOneSegment.addRightSide(1); # 
          
    for aSegment in self.listOfSegments :
      self.eq_IcanOnlyBeInOneSegment.addSummand(aSegment.mod.var_onSeg, 1);                        

    #################################
    ## 2. Gleichungen der Segmente ##
    # eq: -aSegment.onSeg(t) + aSegment.lambda1(t) + aSegment.lambda2(t)  = 0    
    for aSegment in self.listOfSegments:
        aNameOfEq = 'Lambda_onSeg_' + str(aSegment.index)
        
        eq_Lambda_onSeg = cEquation(aNameOfEq,self,modBox)
        eq_Lambda_onSeg.addSummand(aSegment.mod.var_onSeg  ,-1);   
        eq_Lambda_onSeg.addSummand(aSegment.mod.var_lambda1, 1);   
        eq_Lambda_onSeg.addSummand(aSegment.mod.var_lambda2, 1);                           
    
    ##################################################
    ## 3. Gleichungen für die Variablen mit lambda: ##
    #   z.B. Gleichungen für Q_th mit lambda
    #  eq: - Q_th(t) + sum(Q_th_1_j * lambda_1_j + Q_th_2_j * lambda_2_j) = 0
    #  mit -> j                   = Segmentnummer 
    #      -> Q_th_1_j, Q_th_2_j  = Stützstellen des Segments (können auch Vektor sein)
    
    for aVar in self.segmentsOfVars.keys():
      # aVar = aFlow.mod.var_val
      eqLambda = cEquation(aVar.label + '_lambda', self, modBox) # z.B. Q_th(t)
      eqLambda.addSummand(aVar, -1)        
      for aSegment in self.listOfSegments:
        #  Stützstellen einfügen:
        stuetz1 = aSegment.samplePoints[aVar][0]
        stuetz2 = aSegment.samplePoints[aVar][1]
        # wenn Stützstellen TS_vector:
        if isinstance(stuetz1, cTS_vector):          
          samplePoint1 = stuetz1.d_i
          samplePoint2 = stuetz2.d_i
        # wenn Stützstellen Skalar oder array
        else:
          samplePoint1 = stuetz1
          samplePoint2 = stuetz2     
        
        eqLambda.addSummand(aSegment.mod.var_lambda1, samplePoint1) # Spalte 1 (Faktor kann hier Skalar sein oder Vektor)
        eqLambda.addSummand(aSegment.mod.var_lambda2, samplePoint2) # Spalte 2 (Faktor kann hier Skalar sein oder Vektor)

  # extract the 2 TS_vectors for the segment:
  def __extractSamplePoints4Segment(samplePointsOfAllSegments, nrOfSegment):
      samplePoints4Segment = {}
      # für alle Variablen Segment-Stützstellen holen:             
      aSpalteOfSecStart = (nrOfSegment)*2  # 0, 2, 4
      for aVar in samplePointsOfAllSegments.keys():
        # 1. und 2. Stützstellen des Segments auswählen:  
        samplePoints4Segment[aVar] = samplePointsOfAllSegments[aVar][aSpalteOfSecStart : aSpalteOfSecStart+2]        
      return samplePoints4Segment

 
class cFeatureLinearSegmentSet(cFeatureLinearSegmentVars) : 
  # TODO: beser wäre segmentsOfVars, aber schwierig, weil diese hier noch nicht vorhanden sind!
  def __init__(self, label, owner, segmentsOfFlows_TS, get_var_on = None, checkListOfFlows = None ):   
    # segementsData - Elemente sind Listen!.
    # segmentsOfFlows = {Q_fu: [ 5  , 10,  10, 22], # je zwei Werte bilden ein Segment. Zeitreihenabbildung über arrays!!!
    #                    P_el: [ 2  , 5,    5, 8 ],
    #                    Q_th: [ 2.5, 4,    4, 12]}
    # -> auch einzelne zulässige Punkte können über Segment ausgedrückt werden, z.B. [5, 5]
    
    self.segmentsOfFlows_TS = segmentsOfFlows_TS 
    self.get_var_on = get_var_on
    self.checkListOfFlows = checkListOfFlows
    super().__init__(label, owner)
  
  def declareVarsAndEqs(self, modBox):
    # 1. Variablen-Segmente definieren:
    segmentsOfVars = {}
    for flow in self.segmentsOfFlows_TS:
      segmentsOfVars[flow.mod.var_val] = self.segmentsOfFlows_TS[flow]    
    
    checkListOfVars = []
    for flow in self.checkListOfFlows:
      checkListOfVars.append(flow.mod.var_val)

    # hier erst Variablen vorhanden un damit segmentsOfVars definierbar!
    super().defineSegments(segmentsOfVars, var_on = self.get_var_on(), checkListOfVars = checkListOfVars) # todo: das ist nur hier, damit schon variablen Bekannt

    # 2. declare vars:      
    super().declareVarsAndEqs(modBox)
  
# Abschnittsweise linear, 1 Abschnitt:
class cSegment(cFeature) :
  def __init__(self, label, owner, samplePoints, index):

    super().__init__(label, owner)

    self.label  = label
    self.samplePoints = samplePoints
    self.index = index    
    
  def declareVarsAndEqs(self, modBox):
    aLen          = modBox.nrOfTimeSteps
    self.mod.var_onSeg   = cVariable('onSeg_'   + str(self.index), aLen, self, modBox, isBinary = True)   # Binär-Variable
    self.mod.var_lambda1 = cVariable('lambda1_' + str(self.index), aLen, self, modBox, min = 0 , max = 1) # Wertebereich 0..1
    self.mod.var_lambda2 = cVariable('lambda2_' + str(self.index), aLen, self, modBox, min = 0 , max = 1) # Wertebereich 0..1    


# Verhindern gleichzeitig mehrere Flows > 0 
class cFeatureAvoidFlowsAtOnce(cFeature):
  
  def __init__(self, label, owner, flows, typ = 'classic'):  
    super().__init__(label, owner)
    self.flows = flows
    self.typ   = typ
    assert len(self.flows) >= 2, 'Beachte für Feature AvoidFlowsAtOnce: Mindestens 2 Flows notwendig'
    
    
  def finalize(self):
    super().finalize
    # Beachte: Hiervor muss featureOn in den Flows existieren!
    aFlow : cFlow

    if self.typ == 'classic':
      # "classic" -> alle Flows brauchen Binärvariable:        
      for aFlow in self.flows:
        aFlow.activateOnValue()
        
    elif self.typ == 'new':
      # "new" -> n-1 Flows brauchen Binärvariable: (eine wird eingespart)
        
      # 1. Get nr of existing on_vars in Flows
      self.nrOfExistingOn_vars = 0
      for aFlow in self.flows:
         self.nrOfExistingOn_vars += aFlow.featureOn.useOn
      
      # 2. Add necessary further flow binaries:                
      # Anzahl on_vars solange erhöhen bis mindestens n-1 vorhanden:
      i = 0
      while self.nrOfExistingOn_vars < (len(self.flows) - 1):
        aFlow = flows[i]
        # Falls noch nicht on-Var für flow existiert, dann erzwingen:
        if not aFlow.featureOn.useOn : 
          aFlow.activateOnValue()
          self.nrOfExistingOn_vars += 1
        i += 1

      
  def doModeling(self, modBox, timeIndexe):
    # Nur 1 Flow aktiv! Nicht mehrere Zeitgleich!    
    # "classic":
    # eq: sum(flow_i.on(t)) <= 1.1 (1 wird etwas größer gewählt wg. Binärvariablengenauigkeit)
    # "new": 
    # eq: flow_1.on(t) + flow_2.on(t) + .. + flow_i.val(t)/flow_i.max <= 1 (1 Flow ohne Binärvariable!)


    # Anmerkung: Patrick Schönfeld (oemof, custom/link.py) macht bei 2 Flows ohne Binärvariable dies:
    # 1)	bin + flow1/flow1_max <= 1
    # 2)	bin - flow2/flow2_max >= 0
    # 3)    geht nur, wenn alle flow.min >= 0
    # --> könnte man auch umsetzen (statt activateOnValue() für die Flows, aber sollte aufs selbe wie "new" kommen)

    self.eq_flowLock = cEquation('flowLock', self, modBox, eqType = 'ineq')
    # Summanden hinzufügen:
    for aFlow in self.flows:
      # + flow_i.on(t):
      if aFlow.mod.var_on is not None : 
        self.eq_flowLock.addSummand(aFlow.mod.var_on , 1)    
      # + flow_i.val(t)/flow_i.max
      else: # nur bei "new"
        assert aFlow.min >= 0, 'cFeatureAvoidFlowsAtOnce(): typ "new" geht nur für Flows mit min >= 0!'
        self.eq_flowLock.addSummand(aFlow.mod.var_val, 1/aFlow.max)

    if self.typ == 'classic':
      self.eq_flowLock.addRightSide(1.1) # sicherheitshalber etwas mehr, damit auch leicht größer Binärvariablen 1.00001 funktionieren.    
    elif typ == 'new':
      self.eq_flowLock.addRightSide(1) # TODO: hier ggf. Problem bei großen Binärungenauigkeit!!!!

## Klasse, die in Komponenten UND Flows benötigt wird: ##
class cFeatureOn(cFeature) :
  # def __init__(self, featureOwner, nameOfVariable, useOn, useSwitchOn):  
  # #   # on definierende Variablen:
  # #   self.featureOwner = featureOwner
  # #   self.nameOfVariable = nameOfVariable
  # #   self.flows  = flows
  # #   self.mod.var_on = None
  def __init__(self, owner, flowsDefiningOn, on_valuesBeforeBegin, switchOnCosts, costsPerRunningHour, onHours_min = None, onHours_max = None, switchOn_maxNr = None, useOn_explicit = False, useSwitchOn_explicit=False):
    super().__init__('featureOn', owner)
    self.flowsDefiningOn     = flowsDefiningOn
    self.on_valuesBeforeBegin = on_valuesBeforeBegin
    self.switchOnCosts       = switchOnCosts
    self.costsPerRunningHour = costsPerRunningHour
    self.onHours_min  = onHours_min
    self.onHours_max  = onHours_max
    self.switchOn_maxNr      = switchOn_maxNr
    # default:
    self.useOn       = False
    self.useSwitchOn = False

    # Notwendige Variablen entsprechend der übergebenen Parameter:        
    paramsForcingOn = [costsPerRunningHour, onHours_min, onHours_max] 
    if any(param is not None for param in paramsForcingOn):
      self.useOn = True
    
    paramsForcingSwitchOn = [switchOnCosts, switchOn_maxNr]
    if any(param is not None for param in paramsForcingSwitchOn):
      self.useOn = True
      self.useSwitchOn = True    
    
    self.useOn       = self.useOn       | useOn_explicit
    self.useSwitchOn = self.useSwitchOn | useSwitchOn_explicit

  # Befehl von außen zum Erzwingen einer On-Variable:
  def activateOnValueExplicitly(self):
    self.useOn = True
  # varOwner braucht die Variable auch:
  def getVar_on(self)  :
    return self.mod.var_on
  def getVars_switchOnOff(self):
    return self.mod.var_switchOn, self.mod.var_switchOff

  #   # Variable wird erstellt und auch gleich in featureOwner registiert:
  #      
  #   # ## Variable als Attribut in featureOwner übergeben:
  #   # # TODO: ist das so schick? oder sollte man nicht so versteckt Attribute setzen?
  #   # # Check:
  #   # if (hasattr(self.featureOwner, 'var_on')) and (self.featureOwner.mod.var_on == None) :
  #   #   self.featureOwner.mod.var_on = self.mod.var_on
  #   # else :
  #   #   raise Exception('featureOwner ' + self.featureOwner.label + ' has no attribute var_on or it is already used')
  
  def declareVarsAndEqs(self,modBox):
    # Beachte: Variablen gehören nicht diesem Element, sondern varOwner (meist ist das der featureOwner)!!!  
    # Var On:
    if self.useOn : 
      #Before-Variable:
      self.mod.var_on      = cVariableB('on', modBox.nrOfTimeSteps, self.owner, modBox, isBinary = True)
      self.mod.var_on.activateBeforeValues(esBeforeValue = self.on_valuesBeforeBegin[0], beforeValueIsStartValue = False)
      self.mod.var_onHours = cVariable('onHours', 1, self.owner, modBox, min = self.onHours_min, max = self.onHours_max) # wenn max/min = None, dann bleibt das frei
    else :
      self.mod.var_on = None      
      self.mod.var_onHours = None
      
    # Var SwitchOn
    if self.useSwitchOn:
      self.mod.var_switchOn  = cVariable('switchOn' , modBox.nrOfTimeSteps, self.owner, modBox, isBinary = True)
      self.mod.var_switchOff = cVariable('switchOff', modBox.nrOfTimeSteps, self.owner, modBox, isBinary = True)  
      self.mod.var_nrSwitchOn = cVariable('nrSwitchOn' , 1, self.owner, modBox, max = self.switchOn_maxNr) # wenn max/min = None, dann bleibt das frei
    else:
      self.mod.var_switchOn  = None
      self.mod.var_switchOff = None
      self.mod.var_nrSwitchOn = None

    
  def doModeling(self,modBox,timeIndexe):
    eqsOwner = self
    if self.useOn       : self.__addConstraintsForOn               (eqsOwner, self.flowsDefiningOn, modBox, timeIndexe)
    if self.useSwitchOn : self.__addConstraintsForSwitchOnSwitchOff(eqsOwner,                       modBox, timeIndexe)      
    
  def __addConstraintsForOn(self, eqsOwner, flowsDefiningOn, modBox, timeIndexe):
      # % Bedingungen 1) und 2) müssen erfüllt sein:
      
      # % Anmerkung: Falls "abschnittsweise linear" gewählt, dann ist eigentlich nur Bedingung 1) noch notwendig 
      # %            (und dann auch nur wenn erstes Segment bei Q_th=0 beginnt. Dann soll bei Q_th=0 (d.h. die Maschine ist Aus) On = 0 und segment1.onSeg = 0):)
      # %            Fazit: Wenn kein Performance-Verlust durch mehr Gleichungen, dann egal!      

      nrOfFlows = len(flowsDefiningOn)
      assert nrOfFlows > 0 , 'Achtung: mindestens 1 Flow notwendig'      
      #######################################################################
      #### Bedingung 1) ####
     
      # Glg. wird erstellt und auch gleich in featureOwner registiert:
      eq1 = cEquation('On_Constraint_1', eqsOwner , modBox, eqType = 'ineq')
      # TODO: eventuell label besser über  nameOfIneq = [aOnVariable.name '_Constraint_1']; % z.B. On_Constraint_1

      # Wenn nur 1 Leistungsvariable (!Unterscheidet sich von >1 Leistungsvariablen wg. Minimum-Beachtung!):
      if nrOfFlows == 1:
        ## Leistung<=MinLeistung -> On = 0 | On=1 -> Leistung>MinLeistung
        # eq: Q_th(t) - max(Epsilon, Q_th_min) * On(t) >= 0  (mit Epsilon = sehr kleine Zahl, wird nur im Falle Q_th_min = 0 gebraucht)
        # gleichbedeutend mit eq: -Q_th(t) + max(Epsilon, Q_th_min)* On(t) <= 0 
        aFlow = flowsDefiningOn[0]
        eq1.addSummand(aFlow.mod.var_val , -1                                       ,timeIndexe)
        # wenn variabler Nennwert:
        if aFlow.nominal_val is None:
          min_val = aFlow.investArgs.min_investmentSize * aFlow.min_rel.d_i # kleinst-Möglichen Wert nutzen. (Immer noch math. günstiger als Epsilon)
        # wenn fixer Nennwert
        else:
          min_val = aFlow.nominal_val     * aFlow.min_rel.d_i
          
        eq1.addSummand(self.mod.var_on   , 1*np.maximum(modBox.epsilon, min_val), timeIndexe) # % aLeistungsVariableMin kann hier Skalar oder Zeitreihe sein!    
     
      # Bei mehreren Leistungsvariablen:
      else:
        
        # Nur wenn alle Flows = 0, dann ist On = 0
        ## 1) sum(alle Leistung)=0 -> On = 0 | On=1 -> sum(alle Leistungen) > 0
        # eq: - sum(alle Leistungen(t)) + Epsilon * On(t) <= 0
        for aFlow in flowsDefiningOn:        
          eq1.addSummand(aFlow.mod.var_val , -1      , timeIndexe)
        eq1.addSummand(self.mod.var_on , 1*modBox.epsilon , timeIndexe) # % aLeistungsVariableMin kann hier Skalar oder Zeitreihe sein!          
      
      #######################################################################
      #### Bedingung 2) ####

      # Glg. wird erstellt und auch gleich in featureOwner registiert:
      eq2 = cEquation('On_Constraint_2', eqsOwner ,modBox, eqType = 'ineq')
      # Wenn nur 1 Leistungsvariable:
        #  eq: Q_th(t) <= Q_th_max * On(t)
        # (Leistung>0 -> On = 1 | On=0 -> Leistung<=0)
      # Bei mehreren Leistungsvariablen:
        ## sum(alle Leistung) >0 -> On = 1 | On=0 -> sum(Leistung)=0
        #  eq: sum( Leistung(t,i))              - sum(Leistung_max(i))             * On(t) <= 0
        #  --> damit Gleichungswerte nicht zu groß werden, noch durch nrOfFlows geteilt: 
        #  eq: sum( Leistung(t,i) / nrOfFlows ) - sum(Leistung_max(i)) / nrOfFlows * On(t) <= 0
      sumOfFlowMax = 0
      for aFlow in flowsDefiningOn:
        eq2.addSummand(aFlow.mod.var_val,  1 / nrOfFlows       , timeIndexe)
        # wenn variabler Nennwert:
        if aFlow.nominal_val is None:    
          sumOfFlowMax += aFlow.max_rel.d_i * aFlow.investArgs.max_investmentSize # der maximale Nennwert reicht als Obergrenze hier aus. (immer noch math. günster als BigM)
        else: 
          sumOfFlowMax += aFlow.max_rel.d_i * aFlow.nominal_val
        
      eq2.addSummand(self.mod.var_on , - sumOfFlowMax/ nrOfFlows, timeIndexe) #         
      if sumOfFlowMax / nrOfFlows > 1000 : log.warning('!!! ACHTUNG in ' + self.owner.label_full + ' : Binärdefinition mit großem Max-Wert ('+str(int(sumOfFlowMax / nrOfFlows))+'). Ggf. falsche Ergebnisse !!!')
  
  
  
  
      #######################################################################
      #### Anzahl Betriebsstunden ####
      # eq: onHours = sum(on(t)*dt)
      
      eq_OnHours = cEquation('onHours', eqsOwner ,modBox)
      eq_OnHours.addSummand(     self.mod.var_onHours,  1)
      eq_OnHours.addSummandSumOf(self.mod.var_on     , -1 * modBox.dtInHours)
      
  
  
  def __addConstraintsForSwitchOnSwitchOff(self,eqsOwner, modBox, timeIndexe):
      # % Schaltänderung aus On-Variable
      # % SwitchOn(t)-SwitchOff(t) = On(t)-On(t-1) 
      
      eq_SwitchOnOff_andOn = cEquation('SwitchOnOff_andOn',eqsOwner,modBox)
      eq_SwitchOnOff_andOn.addSummand(self.mod.var_switchOn  ,  1, timeIndexe[1:  ]) # SwitchOn(t)
      eq_SwitchOnOff_andOn.addSummand(self.mod.var_switchOff , -1, timeIndexe[1:  ]) # SwitchOff(t)
      eq_SwitchOnOff_andOn.addSummand(self.mod.var_on        , -1, timeIndexe[1:  ]) # On(t)
      eq_SwitchOnOff_andOn.addSummand(self.mod.var_on        , +1, timeIndexe[0:-1]) # On(t-1)
            
      
      ## Ersten Wert SwitchOn(t=1) bzw. SwitchOff(t=1) festlegen
      # eq: SwitchOn(t=1)-SwitchOff(t=1) = On(t=1)- ValueBeforeBeginOfTimeSeries;      

      eq_SwitchOnOffAtFirstTime = cEquation('SwitchOnOffAtFirstTime',eqsOwner,modBox) 
      firstIndex = timeIndexe[0] # nur erstes Element!
      eq_SwitchOnOffAtFirstTime.addSummand(self.mod.var_switchOn , 1, firstIndex)
      eq_SwitchOnOffAtFirstTime.addSummand(self.mod.var_switchOff,-1, firstIndex)
      eq_SwitchOnOffAtFirstTime.addSummand(self.mod.var_on       ,-1, firstIndex)
      # eq_SwitchOnOffAtFirstTime.addRightSide(-on_valuesBefore[-1]) # letztes Element der Before-Werte nutzen,  Anmerkung: wäre besser auf lhs aufgehoben  
      eq_SwitchOnOffAtFirstTime.addRightSide(-self.mod.var_on.beforeVal()) # letztes Element der Before-Werte nutzen,  Anmerkung: wäre besser auf lhs aufgehoben  
      
      ## Entweder SwitchOff oder SwitchOn
      # eq: SwitchOn(t) + SwitchOff(t) <= 1 
    
      ineq = cEquation('SwitchOnOrSwitchOff',eqsOwner,modBox,eqType = 'ineq')
      ineq.addSummand(self.mod.var_switchOn , 1)
      ineq.addSummand(self.mod.var_switchOff, 1) 
      ineq.addRightSide(1)  

      
      ## Anzahl Starts:
      # eq: nrSwitchOn = sum(SwitchOn(t))  
      
      eq_NrSwitchOn = cEquation('NrSwitchOn', eqsOwner, modBox)
      eq_NrSwitchOn.addSummand(     self.mod.var_nrSwitchOn,  1)
      eq_NrSwitchOn.addSummandSumOf(self.mod.var_switchOn  , -1)
      

  def addShareToGlobals(self,globalComp,modBox) :        
    
      # Anfahrkosten:
    if self.switchOnCosts is not None : #and any(self.switchOnCosts.d_i != 0):
      globalComp.addShareToOperation(self.mod.var_switchOn, self.switchOnCosts, 1)
    # Betriebskosten:
    if self.costsPerRunningHour is not None : #and any(self.costPerRunningHour):
      globalComp.addShareToOperation(self.mod.var_on, self.costsPerRunningHour, modBox.dtInHours)
      # globalComp.costsOfOperating_eq.addSummand(self.mod.var_on, np.multiply(self.costsPerRunningHour.d_i, modBox.dtInHours))# np.multiply = elementweise Multiplikation          
        
    
      

# TODO: als cFeature_TSShareSum
class cFeature_ShareSum(cFeature): #(ME = ModelingElement)
# sharesAreTS = True : 
#   Output: 
#     var_all (TS), var_sum
#   variables:
#     sum_TS (Zeitreihe)
#     sum    (Skalar)
#   Equations: 
#     eq_sum_TS : sum_TS = sum(share_TS_i) # Zeitserie
#     eq_sum    : sum    = sum(sum_TS(t)) # skalar

# sharesAreTS = False: 
#   Output: 
#     var_sum
#   Equations:
#     eq_sum   : sum     = sum(share_i) # skalar
  
  def __init__(self, label, owner, sharesAreTS, maxOfSum = None, minOfSum = None):
    super().__init__(label, owner)
    self.sharesAreTS = sharesAreTS
    self.maxOfSum    = maxOfSum
    self.minOfSum    = minOfSum
    # self.effectType = effectType    

  # def setProperties(self, min = 0, max = nan)

  def declareVarsAndEqs(self, modBox):
    super().declareVarsAndEqs(modBox)
    
    # TODO: summe auch über Bus abbildbar!
    #   -> aber Beachte Effekt ist nicht einfach gleichzusetzen mit Flow, da hier eine Menge z.b. in € im Zeitschritt übergeben wird
    # variable für alle TS zusammen (TS-Summe):
    if self.sharesAreTS:
      self.mod.var_sum_TS = cVariable('sum_TS', modBox.nrOfTimeSteps, self, modBox) # TS      
    
    # Variable für Summe (Skalar-Summe):
    self.mod.var_sum = cVariable('sum', 1                   , self, modBox, min = self.minOfSum, max = self.maxOfSum) # Skalar
    
    # Gleichungen schon hier definiert, damit andere MEs beim modeling Beiträge eintragen können:      
    if self.sharesAreTS:
      self.eq_sum_TS = cEquation('bilanz', self, modBox)
    self.eq_sum = cEquation('sum', self, modBox)    


  def doModeling(self, modBox, timeIndexe):
    if self.sharesAreTS:
      # eq: sum_TS = sum(share_TS_i) # TS
      self.eq_sum_TS.addSummand(self.mod.var_sum_TS, -1)
      # eq: sum = sum(sum_TS(t)) # skalar
      self.eq_sum.addSummandSumOf(self.mod.var_sum_TS,  1)
      self.eq_sum.addSummand     (self.mod.var_sum   , -1)
    else:
      # eq: sum = sum(share_i) # skalar
      self.eq_sum.addSummand(self.mod.var_sum, -1)
      
  
  # Beiträge zu Effekt_Sum registrieren:    
  # factor : TS oder skalar, bei sharesAreTS=False nur skalar
  def addConstantShare(self, factor1, factor2):
    self.addShare(self, None, factor1, factor2)
  
  def addVariableShare(self, variable, factor1, factor2): # if variable = None, then fix Share
    if variable is None : raise Exception('addVariableShare() needs variable as input or use addConstantShare() instead')
    self.addShare(variable, factor1, factor2)

  # allgemein variable oder constant (dann variable = None):
  # if variable = None, then fix Share    
  def addShare(self, variable, factor1, factor2):
        
    if self.sharesAreTS:             
      
      # Falls cTS_vector, Daten auslesen:
      if isinstance(factor1, cTS_vector) : factor1 = factor1.d_i
      if isinstance(factor2, cTS_vector) : factor2 = factor2.d_i
      
      factorOfSummand = np.multiply(factor1, factor2) # np.multiply = elementweise Multiplikation          
      ## Share zu TS-equation hinzufügen:
      # if constant share:      
      if variable is None:        
        self.eq_sum_TS.addRightSide(-1 * factorOfSummand) 
      # if variable share:
      else:
        self.eq_sum_TS.addSummand(variable, factorOfSummand)
        
      
    else:
      assert (not(isinstance(factor1, cTS_vector))) & (not(isinstance(factor2, cTS_vector))), 'factor1 und factor2 müssen Skalare sein, da shareSum ' + self.label + 'skalar ist'
      factorOfSummand = factor1 * factor2
      ## Share zu skalar-equation hinzufügen:
      # if constant share:
      if variable is None:
        self.eq_sum.addRightSide(-1 * factorOfSummand)
      # if variable share:
      else:
        self.eq_sum.addSummand(variable, factorOfSummand)


# Sammlung von Props für Investitionskosten (für cFeatureInvest)
class cInvestArgs(cArgsClass):
  
  new_init_args = [cArg('fixCosts'              ,'costs','costs scalar'  , 'feste Investitionskosten (!annuisiert für Zeitraum!)'),
                   cArg('investmentSize_is_fixed' ,'param','boolean', 'fester Nennwert oder Nennwert als Optimierungsvariable'),
                   cArg('investment_is_optional','param','boolean', 'kann Element in der Optimierung weggelassen werden (und damit keine Kosten)'),
                   cArg('specificCosts'         ,'costs','costs scalar', 'specific costs, z.B. in €/kW_nominal'),
                   cArg('costsInInvestsizeSegments', 'special', 'special','linear relation in segments, [invest_segments, cost_segments], z.B. [[5, 50, 50, 100], {costs:[10,100,100,160], CO2:[50, 400, 400, 750]}], with this you can also realise valid segments of investSize'),
                   cArg('min_investmentSize'       ,'param','scalar', 'Min nominal value (only if: nominal_val_is_fixed = False)'),
                   cArg('max_investmentSize'    ,'param','scalar', 'Max nominal value (only if: nominal_val_is_fixed = False)')  
                   ]
  not_used_args = [] 
  
  def __init__(self, 
               fixCosts = 0,             # Investkosten
               investmentSize_is_fixed = True, # True: fixed nominal value; false: nominal_value als optimization-variable)
               investment_is_optional = True,  # Investition ist weglassbar
               specificCosts = 0,        # costs per Flow-Unit/Storage-Size/...
               costsInInvestsizeSegments = None,
               min_investmentSize = 0,   # nur wenn nominal_val_is_fixed = False
               max_investmentSize = 1e9, # nur wenn nominal_val_is_fixed = False
               **kwargs): 

    self.fixCosts = fixCosts
    self.investmentSize_is_fixed = investmentSize_is_fixed
    self.investment_is_optional = investment_is_optional
    self.specificCosts = specificCosts
    self.costsInInvestsizeSegments = costsInInvestsizeSegments
    self.min_investmentSize = min_investmentSize
    self.max_investmentSize = max_investmentSize
        
    super().__init__(**kwargs)
      

class cFeatureInvest(cFeature):       
  
  # -> var_name            : z.B. "nominal_val", "capacity_inFlowHours"
  # -> fixedInvestmentSize : nominal_val, capacity_inFlowHours, ...
  # -> definingVar         : z.B. flow.mod.var_val
  # -> min_rel,max_rel     : ist relatives Min,Max der definingVar bzgl. investmentSize
  
  @property  
  def _existOn(self): # existiert On-variable
    if self.featureOn is None:
      existOn = False
    else:
      existOn = self.featureOn.useOn
    return existOn
        
  def __init__(self, nameOfInvestmentSize, owner, investArgs:cInvestArgs, min_rel, max_rel, val_rel, investmentSize, featureOn = None):
    super().__init__('invest', owner)
    self.nameOfInvestmentSize = nameOfInvestmentSize
    self.owner = owner
    self.args = investArgs        
    self.definingVar = None
    self.max_rel = max_rel
    self.min_rel = min_rel
    self.val_rel = val_rel
    self.fixedInvestmentSize = investmentSize # nominalValue
    self.featureOn = featureOn

    self.checkPlausibility()
    
    # segmented investcosts:
    self.featureLinearSegments = None
    if self.args.costsInInvestsizeSegments is not None:
      self.featureLinearSegments = cFeatureLinearSegmentVars('segmentedInvestcosts', self)
    
  def checkPlausibility(self):    
    # Check fixedInvestmentSize:
    # todo: vielleicht ist es aber auch ok, wenn der nominal_val belegt ist und einfach nicht genutzt wird....
    if self.args.investmentSize_is_fixed:      
      assert ((self.fixedInvestmentSize is not None) and (self.fixedInvestmentSize != 0)) , 'fixedInvestmentSize muss gesetzt werden'
    else:
      assert self.fixedInvestmentSize is None, '!' + self.nameOfInvestmentSize + ' of ' +self.owner.label_full +' must be None if investmentSize is variable'

  def getMinMaxOfDefiningVar(self):      
    
    # Wenn fixer relativer Lastgang:
    if self.val_rel is not None:
      # max_rel = min_rel = val_rel !
      min_rel_eff = self.val_rel.d_i
      max_rel_eff = min_rel_eff
    else:
      min_rel_eff = self.min_rel.d_i
      max_rel_eff = self.max_rel.d_i

    valIsNotFixAndOnIsUsed = (self.val_rel is None) and ((self.featureOn is not None) and (self.featureOn.useOn))
          
    # min-Wert:
    if valIsNotFixAndOnIsUsed or self.args.investment_is_optional: 
      lb = 0 # kann ausgehen bzw. (immer) null sein
    else :
      if self.args.investmentSize_is_fixed:
        lb = min_rel_eff * self.fixedInvestmentSize # immer an
      else:
        lb = min_rel_eff * self.args.min_investmentSize # investSize is variabel
    #  max-Wert:
    if self.args.investmentSize_is_fixed:
      ub = max_rel_eff * self.fixedInvestmentSize
    else :
      ub = max_rel_eff * self.args.max_investmentSize # investSize is variabel
    
    # ub und lb gleich, dann fix:
    if np.all(ub == lb): #np.all -> kann listen oder werte vergleichen
      fix_value = ub
      ub = None
      lb = None
    else :
      fix_value = None
    
    return (lb,ub,fix_value)

  # Variablenreferenz kann erst später hinzugefügt werden, da erst später erstellt:
  # todo-> abändern durch cVariable-Dummies
  def setDefiningVar(self, definingVar, definingVar_On):
    self.definingVar    = definingVar
    self.definingVar_On  = definingVar_On
    
  def declareVarsAndEqs(self, modBox):  

    # a) var_investmentSize: (wird immer gebaut, auch wenn fix)           
    
    # lb..ub of investSize unterscheiden:        
    # min:
    if self.args.investment_is_optional: 
      lb = 0                  
    # Wenn invest nicht optional:
    else:
      if self.args.investmentSize_is_fixed: 
        lb = self.fixedInvestmentSize # einschränken, damit P_inv = P_nom !          
      else: 
        lb = self.args.min_investmentSize #      
    # max:
    if self.args.investmentSize_is_fixed:            
      ub = self.fixedInvestmentSize       
    # wenn nicht fixed:
    else:
      ub = self.args.max_investmentSize    
    # Definition:
    
      
    if lb == ub:    
      # fix:
      self.mod.var_investmentSize = cVariable(self.nameOfInvestmentSize, 1, self, modBox, value = lb)
    else:    
      # Bereich:
      self.mod.var_investmentSize = cVariable(self.nameOfInvestmentSize, 1, self, modBox, min = lb, max = ub)


    # b) var_isInvested:
    if self.args.investment_is_optional:      
      self.mod.var_isInvested = cVariable('isInvested', 1, self, modBox, isBinary = True)          


    ## investCosts in Segments: ##
    # wenn vorhanden,
    if self.featureLinearSegments is not None:      
      self._defineCostSegments(modBox)
      self.featureLinearSegments.declareVarsAndEqs(modBox)
 
  # definingInvestcosts in Segments:
  def _defineCostSegments(self, modBox:cModelBoxOfES):
     investSizeSegs = self.args.costsInInvestsizeSegments[0] # segments of investSize
     costSegs       = self.args.costsInInvestsizeSegments[1] # effect-dict with segments as entries
     costSegs = getEffectDictOfEffectValues(costSegs)

     ## 1. create segments for investSize and every effect##
     ## 1.a) add investSize-Variablen-Segmente: ##
     segmentsOfVars = {self.mod.var_investmentSize : investSizeSegs} # i.e. {var_investSize: [0,5, 5,20]}
     
     ## 1.b) je Effekt -> new Variable und zugehörige Segmente ##
     self.mod.var_list_investCosts_segmented = []
     self.investVar_effect_dict = {}# benötigt 
     for aEffect, aSegmentCosts in costSegs.items():
       
       var_investForEffect = self.__create_var_segmentedInvestCost(aEffect, modBox)
       aSegment = {var_investForEffect : aSegmentCosts} # i.e. {var_investCosts_segmented_costs : [0,10, 10,30]}
       segmentsOfVars |= aSegment # 
       self.investVar_effect_dict |= {aEffect: var_investForEffect}
     
     ## 2. on_var: ##
     if self.args.investment_is_optional:
        var_isInvested = self.mod.var_isInvested
     else:
        var_isInvested = None
        
     ## 3. transfer segmentsOfVars to cFeatureLinearSegmentVars: ##
     self.featureLinearSegments.defineSegments(segmentsOfVars, var_on = var_isInvested, checkListOfVars= list(segmentsOfVars.keys()))
     
  def __create_var_segmentedInvestCost(self, aEffect, modBox):
    # define cost-Variable (=costs through segmented Investsize-costs):
    if isinstance(aEffect, cEffectType):
      aStr = aEffect.label
    elif aEffect is None:
      aStr = modBox.es.listOfEffectTypes.standardType().label # Standard-Effekt
    else:
      raise Exception('Given effect (' + str(aEffect) + ') is not an effect!')
    # new variable, i.e for costs, CO2,... :
    var_investForEffect = cVariable('investCosts_segmented_' + aStr , 1, self, modBox, min = 0)
    self.mod.var_list_investCosts_segmented.append(var_investForEffect)
    return var_investForEffect
    
  def doModeling(self, modBox, timeIndexe):    
    assert self.definingVar is not None, 'setDefiningVar() still not executed!'       
    

    # wenn var_isInvested existiert:    
    if self.args.investment_is_optional:
      self._add_defining_var_isInvested(modBox)
      
    # Bereich von definingVar in Abh. von var_investmentSize:
    
    # Wenn fixer relativer Lastgang:
    if self.val_rel is not None:
      self._add_fixEq_of_definingVar_with_var_investmentSize(modBox)
    # Wenn nicht fix:
    else:      
      self._add_max_min_of_definingVar_with_var_investmentSize(modBox) 
     
    # if linear Segments defined:
    if self.featureLinearSegments is not None:
      self.featureLinearSegments.doModeling(modBox, timeIndexe)

  def _add_fixEq_of_definingVar_with_var_investmentSize(self, modBox):
    
    ## Gleichung zw. DefiningVar und Investgröße:    
    # eq: definingVar(t) = var_investmentSize * val_rel
    
    self.eq_fix_via_investmentSize = cEquation('fix_via_InvestmentSize',self, modBox, 'eq')
    self.eq_fix_via_investmentSize.addSummand(self.definingVar, 1)
    self.eq_fix_via_investmentSize.addSummand(self.mod.var_investmentSize, np.multiply(-1, self.val_rel.d_i))
    

  def _add_max_min_of_definingVar_with_var_investmentSize(self, modBox):
 
    ## 1. Gleichung: Maximum durch Investmentgröße ##     
    # eq: definingVar(t) <=                var_investmentSize * max_rel(t)     
    # eq: P(t) <= max_rel(t) * P_inv    
    self.eq_max_via_investmentSize = cEquation('max_via_InvestmentSize',self, modBox, 'ineq')
    self.eq_max_via_investmentSize.addSummand(self.definingVar, 1)
    self.eq_max_via_investmentSize.addSummand(self.mod.var_investmentSize, np.multiply(-1, self.max_rel.d_i))
    
       
    ## 2. Gleichung: Minimum durch Investmentgröße ##        
    
    # Glg nur, wenn nicht Kombination On und fixed:
    if not (self._existOn and self.args.investmentSize_is_fixed):
      self.eq_min_via_investmentSize = cEquation('min_via_investmentSize',self, modBox, 'ineq')
    
    if self._existOn:      
      # Wenn InvestSize nicht fix, dann weitere Glg notwendig für Minimum (abhängig von var_investSize)
      if not self.args.investmentSize_is_fixed:        
        # eq: definingVar(t) >= Big * (On(t)-1) + investmentSize * min_rel(t)
        #     ... mit Big = max(min_rel*P_inv_max, epsilon)
        # (P < min_rel*P_inv -> On=0 | On=1 -> P >= min_rel*P_inv)
        
        # äquivalent zu:.
        # eq: - definingVar(t) + Big * On(t) + min_rel(t) * investmentSize <= Big
        
        Big = helpers.max_args(self.min_rel.d_i * self.args.max_investmentSize, modBox.epsilon)

        self.eq_min_via_investmentSize.addSummand(self.definingVar, -1) 
        self.eq_min_via_investmentSize.addSummand(self.definingVar_On, Big) # übergebene On-Variable
        self.eq_min_via_investmentSize.addSummand(self.mod.var_investmentSize, self.min_rel.d_i)
        self.eq_min_via_investmentSize.addRightSide(Big)
        # Anmerkung: Glg bei Spezialfall min_rel = 0 redundant zu cFeatureOn-Glg.
      else:
        pass # Bereits in cFeatureOn mit P>= On(t)*Min ausreichend definiert    
    else:      
      # eq: definingVar(t) >= investmentSize * min_rel(t)    
      
      self.eq_min_via_investmentSize.addSummand(self.definingVar, -1)
      self.eq_min_via_investmentSize.addSummand(self.mod.var_investmentSize, self.min_rel.d_i)    
      
  #### Defining var_isInvested ####
  def _add_defining_var_isInvested(self, modBox):  
         
    # wenn fixed, dann const:
    if self.args.investmentSize_is_fixed:
      
      # eq: investmentSize = isInvested * nominalValue            
      self.eq_isInvested_1 = cEquation('isInvested_constraint_1', self, modBox, 'eq')      
      self.eq_isInvested_1.addSummand(self.mod.var_investmentSize, -1)
      self.eq_isInvested_1.addSummand(self.mod.var_isInvested, self.fixedInvestmentSize)      
    
    # wenn nicht fix, dann Bereich:
    else:
      
      ## 1. Gleichung (skalar):            
      # eq1: P_invest <= isInvested * investSize_max
      # (isInvested = 0 -> P_invest=0  |  P_invest>0 -> isInvested = 1 ->  P_invest < investSize_max )   

      self.eq_isInvested_1 = cEquation('isInvested_constraint_1', self, modBox, 'ineq')      
      self.eq_isInvested_1.addSummand(self.mod.var_investmentSize,1)           
      self.eq_isInvested_1.addSummand(self.mod.var_isInvested, np.multiply(-1, self.args.max_investmentSize)) # Variable ist Skalar!
          
      ## 2. Gleichung (skalar):                  
      # eq2: P_invest  >= isInvested * max(epsilon, investSize_min)
      # (isInvested = 1 -> P_invest>0  |  P_invest=0 -> isInvested = 0)
      self.eq_isInvested_2 = cEquation('isInvested_constraint_2', self, modBox, 'ineq')    
      self.eq_isInvested_2.addSummand(self.mod.var_investmentSize, -1)
      self.eq_isInvested_2.addSummand(self.mod.var_isInvested, max(modBox.epsilon, self.args.min_investmentSize))
   
        
  def addShareToGlobals(self, globalComp, modBox):      
    ## fixCosts:
    # wenn fixCosts vorhanden:
    if not(self.args.fixCosts is None) and self.args.fixCosts != 0:
      if self.args.investment_is_optional:
        # fix Share to InvestCosts: 
        # share: + isInvested * fixCosts
        globalComp.addShareToInvest(self.mod.var_isInvested, self.args.fixCosts, 1)
      else:
        # share: + fixCosts
        globalComp.addConstantShareToInvest(self.args.fixCosts, 1) # fester Wert hinufügen
    pass
    
    ## specificCosts:
    # wenn specificCosts vorhanden:
    if not (self.args.specificCosts is None):
      # share: + investmentSize (=var)   * specificCosts
      globalComp.addShareToInvest(self.mod.var_investmentSize, self.args.specificCosts, 1)
        
    ## segmentedCosts:
    if self.featureLinearSegments is not None:
      for effect, var_investSegs in self.investVar_effect_dict.items():
        globalComp.addShareToInvest(var_investSegs, {effect:1},1)