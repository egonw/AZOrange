"""
Module for calculating the Mahalanobis distance between an orange example and data object. 
"""
import time
import string
import os

import orange
from AZutilities import dataUtilities
from AZutilities import miscUtilities
from AZutilities import TrainingSet
from AZutilities import Mahalanobis
from AZutilities import quantiles
import AZOrangeConfig as AZOC


NO_OF_NEIGHBORS = 3    # Neighbor info not returned from calcMD

def getTrainingSet(data):

    # Write the data to disk to be able to create the TrainingSet object
    fileName = os.path.join(AZOC.SCRATCHDIR, "tmpTextFile"+str(time.time())+".txt")
    #print "FileName: ",fileName
    fid = open(fileName, "w")
 
    # Create SMILES and ID with artificial values.
    header = ["SMILES", "ID"]

    # Write header
    for attr in data.domain.attributes:
        header.append(attr.name) 
    fid.write(string.join(header, "\t")+"\n")
 
    # Write the data matrix
    for ex in data:
        valueList = ["XXX", "XX"]  # Smiles and ID attributes
        try:
            if ex["Compound Name"] and ex["Molecule SMILES"]:
                valueList = [ex["Molecule SMILES"].value,ex["Compound Name"].value]
        except:
            pass
        for attr in ex:
            valueList.append(str(attr.value))
        # Remove the response value if it exists
        if data.domain.classVar: 
            valueList = valueList[0:len(valueList)-1]
        fid.write(string.join(valueList, "\t")+"\n")
    fid.close() 
    
    # Create the TrainingSet object
    trainingSet = TrainingSet.read_training_set(open(fileName))

    return trainingSet

def rmClassEx(data):

    newDomain = orange.Domain(data.domain.attributes)
    newData = orange.Example(newDomain, data)
    return newData


def rmClass(data):

    newDomain = orange.Domain(data.domain.attributes)
    newData = dataUtilities.DataTable(newDomain, data)
    return newData

def addDummyClass(data):

    print "********************data.domain.classVar*****************"
    print data.domain.classVar
    if not data.domain.classVar:
        newAttr = orange.EnumVariable("dummyClass", values["dummyClass"])
        newDomain = orange.domain(data.domain.attributes, newAttr)
        newData = dataUtilities.DataTable(newDomain, data)
        data = newData
    return data


def calcMahalanobis(data, testData):
    """
    Calculates Mahalanobis distances.
    The data should only contain attributes that are relevant for similarity. OBS data is assumed to have a response variable.
    data - X matrix used to calculate the covariance matrix
    testData - the examples in an ExampleTable object for which to calculate the MDs
    Returns a list of Mahalanobis distances between the examples in testData and training data.
    The elements of the list are dictionaries, giving the Mahalanobis distances to the average (_MD), the nearest neighbor and 
    an average of the 3 nearest neighbors (_train_av3nearest). 
    """

    # Impute any missing values
    averageImputer = orange.ImputerConstructor_average(data)
    data = averageImputer(data)
    averageImputer = orange.ImputerConstructor_average(testData)
    testData = averageImputer(testData)


    #Test if there is any non-numeric value within the dataset
    for ex in testData:
        #It is much faster to address the ex elements by their position instead of the correpondent name
        for idx in range(len(ex.domain.attributes)):
            if not miscUtilities.isNumber(ex[idx].value):
                raise Exception("Cannot calculate Mahalanobis distances. The attribute '" + \
                      ex.domain.attributes[idx].name + "' has non-numeric values. Ex: " + \
                      str(ex[idx].value))

    # Create a trainingSet object. 
    trainingSet = getTrainingSet(data)
    trainingset_descriptor_names = trainingSet.descr_names
    mahalanobisCalculator = Mahalanobis.MahalanobisDistanceCalculator(trainingSet)
    
    MDlist = []
    for ex in testData:
        # Create a numeric vector from the example and assure the same order as in trainingset_descriptor_names
        descriptor_values = []
        for name in trainingset_descriptor_names:
            try:
                descriptor_values.append(float(ex[name].value))
            except:
                raise Exception("Not possible to calculate Mahalanobis distances. Some attribute is not numeric.")
                
        #descriptor_values = [1.5] * len(trainingset_descriptor_names)
        MD = mahalanobisCalculator.calculateDistances(descriptor_values, NO_OF_NEIGHBORS)
        MDlist.append(MD)
    return MDlist


def calcMahalanobisDistanceQuantiles(MD):
    """
    Return the quantile definitions (25%) to produce a Mahalanobis confidence estimate. 
    MD is a list of dictionaries with distances with different Mahalanobis distances. 
    Use the _train_av3nearest key to get the distances.
    """

    mahalanobisDistancelist = []
    for elem in MD:
        mahalanobisDistancelist.append(elem["_train_av3nearest"])
        #mahalanobisDistancelist.append(elem["_train_dist_near1"])

    quantileList = []
    quantileList.append(quantiles.quantile(mahalanobisDistancelist, 0.25, 1))
    quantileList.append(quantiles.quantile(mahalanobisDistancelist, 0.50, 1))
    quantileList.append(quantiles.quantile(mahalanobisDistancelist, 0.75, 1))

    return quantileList


def getMahalanobisResults(predictor):

        if predictor.highConf == None and predictor.lowConf == None:
            return None, None
        testData = dataUtilities.attributeDeselectionData(predictor.exToPred,["SMILEStoPred"])
        trainData = dataUtilities.DataTable(predictor.trainDataPath)
        ExampleFix = dataUtilities.ExFix(trainData.domain,None,False)
        exFixed1 = ExampleFix.fixExample(testData[0])
        if testData.hasMissingValues():
            averageImputer = orange.ImputerConstructor_average(trainData)
            dat = averageImputer(exFixed1)
        else:
            dat = exFixed1

        tab = dataUtilities.DataTable(trainData.domain)
        tab.append(dat)

        MD = calcMahalanobis(trainData, tab)
        near3neighbours = [ (MD[0]["_train_id_near1"], MD[0]["_train_SMI_near1"]), (MD[0]["_train_id_near2"], MD[0]["_train_SMI_near2"]), (MD[0]["_train_id_near3" ], MD[0]["_train_SMI_near3"]) ]
        avg3nearest = MD[0]["_train_av3nearest"]
        if avg3nearest < predictor.highConf:
            confStr = predictor.highConfString
        elif avg3nearest > predictor.lowConf:
            confStr = predictor.lowConfString
        else:
            confStr = predictor.medConfString

	return near3neighbours, confStr

if __name__ == "__main__":
    dataFile = "trainData.txt"
    testDataFile = "testData.txt"
    data = dataUtilities.DataTable(dataFile) 
    testData = dataUtilities.DataTable(testDataFile)

    # This data contains SMILES and ID, which data and ex are assumed not to. 
    attrList = ["SMILES", "ID"]
    data = dataUtilities.attributeDeselectionData(data, attrList)
    testData = dataUtilities.attributeDeselectionData(testData, attrList)

    # Select one ex
    selectionList = []
    for idx in range(len(testData)):
        selectionList.append(0)
    selectionList[0] = 1  # Select first ex
    ex = testData.select(selectionList)

    # One ex in exampleTable
    #MD = calcMahalanobis(data, ex)
    # Multiple ex in exampleTable
    MD = calcMahalanobis(data, testData)
    #print "Returned MD"
    #print MD
    quantiles = calcMahalanobisDistanceQuantiles(MD)
    print quantiles



