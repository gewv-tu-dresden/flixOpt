# -*- coding: utf-8 -*-
"""
Created on Thu Nov 25 09:28:20 2021

@author: Panitz
"""

## Skript für Funktionstest der Aggregation ## (nur reine Zeitreihen, ohne Modellierung des Energiesystems)

# Paket-Importe
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import flixAggregation as flixAgg
import tsam.timeseriesaggregation as tsam
import copy 

from flixStructure import *
from flixComps    import *

useTiedoData = True
extremePeriodMethod = 'None'
extremePeriodMethod = 'new_cluster_center'

if useTiedoData:

  # Daten einlesen
  ts_raw = pd.read_csv('Zeitreihen2020.csv', index_col=0)
  ts_raw = ts_raw.sort_index()

  #ts = ts_raw['2020-01-01 00:00:00':'2020-12-31 23:45:00']  # EDITIEREN FÜR ZEITRAUM

  ts = ts_raw['2020-01-01 00:00:00':'2020-12-31 23:45:00']
  ts['Kohlepr.€/MWh'] = 4.6

  ts.set_index(pd.to_datetime(ts.index), inplace = True)   # str to datetime
  
else:

  # Beispiel durchlaufen lassen:
  from ..TestExample import Main_example_FlixOpt
  
  print(flix.es.allTSinMEs)
  

  
  # clear Skalare
  newTSList = [item for item in flix.es.allTSinMEs if item.isArray]
  print(newTSList)
  TS: cTS_vector
  for TS in newTSList:
    print(TS.label_full)
    
  
  TS:newTSList[0]
  print(TS.label)
  print(TS.d_i)


  
noOfPeriods = 25
hoursPerPeriod = 24

# Erstellen des aggregation objects
aggregation = tsam.TimeSeriesAggregation(ts,
                                        noTypicalPeriods=noOfPeriods,
                                        hoursPerPeriod=hoursPerPeriod,
                                        resolution=0.25,
                                        clusterMethod='k_means',
                                        extremePeriodMethod=extremePeriodMethod, #flixi: 'None'/'new_cluster_center'
                                        addPeakMax=['P_Netz/MW', 'Q_Netz/MW', 'Strompr.€/MWh'],
                                        addPeakMin=['Strompr.€/MWh']
                                        )


res_data_raw     = aggregation.createTypicalPeriods()
predictedPeriods = aggregation.predictOriginalData()
aggregation.clusterPeriodIdx



# Energiesystemmodell erstellen
esm1 = flixAgg.flixAggregation(name='TestAgg',  # Name des Modells, Ergebnisse werden so gespeichert
                             timeseries=ts,  # Verwendete Zeitreihe
                             hoursPerTimeStep=0.25,  # Auflösung, hier Viertelstundenwerte
                             hasTSA=True,  # Auswahl, ob Zeitreihenaggregation
                             hoursPerPeriod=hoursPerPeriod,  # gewünschte Periodenlänge, f#alls Zeitreihenaggregation
                             noTypicalPeriods=noOfPeriods,  # Anzahl typischer Perioden, falls Zeitreihenaggregation
                             # useExtremePeriods=False  # sollen Extremperioden verwendet werden? falls ja, werden vier zusätzliche typ. Perioden erstellt
                             useExtremePeriods=True # sollen Extremperioden verwendet werden? falls ja, werden vier zusätzliche typ. Perioden erstellt
                             )

esm1.cluster()
esm1.declareTimeSets()        
esm1.addTimeseriesData()

esm1.saveResults()  # Speichern von rohen Ergebnissen und Parametern
esm1.saveAgg()  # Speichern der aggregierten Zeitreihen

############ Plot ############


tsAgg = esm1.totalTimeseries_t


tsPlot = ts.reset_index()
months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
xticks = [0, 2976, 5760, 8732, 11612, 14588, 17468, 20444, 23420, 26300, 29280, 32160, 35136]




def plotTS(data, periodlength, vmin, vmax, title):
    fig, axes = plt.subplots(figsize = [14, 4], dpi = 100, nrows = 1, ncols = 1)
    stacked, timeindex = tsam.unstackToPeriods(copy.deepcopy(data), periodlength)
    cax = axes.imshow(stacked.values.T, interpolation = 'nearest', vmin = vmin, vmax = vmax)
    axes.set_aspect('auto')  
    axes.set_ylabel('Stunde am Tag')
    axes.set_yticks([0, 24, 48, 72, 95])
    axes.set_yticklabels(['0', '6', '12', '18', '24'])
    plt.xlabel('Tag')
    plt.title(title)

    fig.subplots_adjust(right = 1.2)
    cbar=plt.colorbar(cax)    
    cbar.set_label('Leistung in MW')
    #plt.savefig('test.pdf', bbox_inches='tight')
    
plotTS(ts   ['P_Netz/MW'], 96, vmin = ts['P_Netz/MW'].min(), vmax = ts['P_Netz/MW'].max(), title = 'Strombedarf')
plotTS(tsAgg['P_Netz/MW'], 96, vmin = tsAgg['P_Netz/MW'].min(), vmax = tsAgg['P_Netz/MW'].max(), title = 'Strombedarf')



def printVergleich(columnStr):

  fig, axes = plt.subplots(figsize = [14, 4], dpi = 100, nrows = 2, ncols = 1)  
  stacked, timeindex = tsam.unstackToPeriods(copy.deepcopy(ts[columnStr]), 96)
  caxOrig = axes.flat[0].imshow(stacked.values.T, interpolation = 'nearest', vmin = ts[columnStr].min(), vmax = ts[columnStr].max())
  axes.flat[0].set_xticklabels([])
  axes.flat[0].set_title('Originaldaten')
  
  stacked, timeindex = tsam.unstackToPeriods(copy.deepcopy(esm1.totalTimeseries[columnStr]), 96)
  cax = axes.flat[1].imshow(stacked.values.T, interpolation = 'nearest', vmin = ts[columnStr].min(), vmax = ts[columnStr].max())
  axes.flat[1].set_xticklabels([])
  axes.flat[1].set_title('Aggregation')
  
  cbar=plt.colorbar(caxOrig, ax=axes[:], shrink=0.8, pad=0.02)    
  cbar.set_label(columnStr, labelpad=15, fontsize=18)
  cbar.ax.tick_params(labelsize=18)
  
  plt.show()

printVergleich('Q_Netz/MW')
printVergleich('P_Netz/MW')


def printVergleichZeit(columnStr):
  fig = plt.figure(figsize =[30,15])
 
  plt.plot(ts   [columnStr], label='Original')#, lw=1.5)
  plt.plot(tsAgg[columnStr], label='Original')#, lw=1.5)
  
  plt.plot(ts   [columnStr][pd.to_datetime('2020-01-20 00:00'):pd.to_datetime('2020-01-20 23:45')], label='Original', lw=1.5)
  plt.plot(tsAgg[columnStr][pd.to_datetime('2020-01-20 00:00'):pd.to_datetime('2020-01-20 23:45')], label='Original', lw=1.5)
  # import matplotlib.dates as mdates
  # # Make ticks on occurrences of each month:
  # ax.xaxis.set_major_locator(mdates.MonthLocator())
  # # Get only the month to show in the x-axis:
  # ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

printVergleichZeit('P_Netz/MW')

plt.show()