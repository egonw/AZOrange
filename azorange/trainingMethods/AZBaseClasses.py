"""
AZBaseClasses
Base Classes for AZ methods.
"""
import orange
import types,os
from AZutilities import dataUtilities

def modelRead(modelFile,verbose = 0,retrunClassifier = True):
    """Get the type of model saved in 'modelPath' and loads the respective model
       Returns the Classifier saved in the respective model path
       It can returns the classifier, or just a tring with the Type: CvSVM, CvANN, PLS or CvRF

            modelRead (modelFile [, verbose = 0] [, retrunClassifier = True] )"""
    modelType = None
    loadedModel = None
    if os.path.isfile(os.path.join(modelFile,"model.svm")):
        modelType =  "CvSVM"
        if not retrunClassifier: return modelType
        from trainingMethods import AZorngCvSVM    
        loadedModel = AZorngCvSVM.CvSVMread(modelFile,verbose)
    elif os.path.isfile(os.path.join(modelFile,"model.ann")):
        modelType =  "CvANN"
        if not retrunClassifier: return modelType
        from trainingMethods import AZorngCvANN
        loadedModel = AZorngCvANN.CvANNread(modelFile,verbose)
    elif os.path.isfile(os.path.join(modelFile,"Model.pls")):
        modelType =  "PLS"
        if not retrunClassifier: return modelType
        from trainingMethods import AZorngPLS
        loadedModel = AZorngPLS.PLSread(modelFile,verbose)
    elif os.path.isfile(os.path.join(modelFile, os.path.split(modelFile)[-1])):
        modelType =  "RF"
        if not retrunClassifier: return modelType
        from trainingMethods import AZorngRF
        loadedModel = AZorngRF.RFread(modelFile,verbose)
    elif os.path.isdir(os.path.join(modelFile,"C0.model")):
        modelType =  "Consensus"
        if not retrunClassifier: return modelType
        from trainingMethods import AZorngConsensus
        loadedModel = AZorngConsensus.Consensusread(modelFile,verbose)
    return loadedModel
 


class AZLearner(orange.Learner):
    """
    Base Class for AZLearners
    It assures that all AZLearners have al teast the setattr method
    Here we can add more methods commun to all Learners which derivates from this class
    """
    def __new__(cls, trainingData = None, name = "AZ learner", **kwds):
        self = orange.Learner.__new__(cls, **kwds)
        self.__dict__.update(kwds)
	self.name = name
        self.basicStat = None
        return self
        
    def __call__(self, trainingData = None, weight = None): 
        if not trainingData:
            print "AZBaseClasses ERROR: Missing training data!"
            self.basicStat = None
            return False
        elif dataUtilities.findDuplicatedNames(trainingData.domain):
            print "AZBaseClasses ERROR: Duplicated names found in the training data. Please use the method dataUtilities.DataTable() when loading a dataset in order to fix the duplicated names and avoid this error."
            self.basicStat = None
            return False
        possibleMetas = dataUtilities.getPossibleMetas(trainingData)
        if possibleMetas:
            print "AZBaseClasses ERROR: Detected attributes that should be considered meta-attributes:"
            for attr in possibleMetas:
                print "    ",attr
            return False
        #Get the Domain basic statistics and save only the desired info in self.basicStat
        basicStat = orange.DomainBasicAttrStat(trainingData)
        self.basicStat = {}
        for attr in trainingData.domain:
            if attr.varType == orange.VarTypes.Discrete:
                self.basicStat[attr.name] = None
            else:       
                self.basicStat[attr.name] = {"min":basicStat[attr].min, "max":basicStat[attr].max}
            
        return True

    def setattr(self, name, value):
        self.__dict__[name] = value


    def convertPriors(self,priors,classVar,getDict = False):
        """Converts the passed priors to a list according to the classVar
              a) returns a list if success convertion
              b) returns None if no priors are to be used, or if the class is not discrete
              b) returns a string with the error message if failed
        """
        if not priors or not classVar or classVar.varType != orange.VarTypes.Discrete:
            return None
        else:
            if type(priors) == str:
                try:
                    InPriors = eval(priors)
                    if InPriors != None and (type(InPriors) not in (dict,list)):
                        raise Exception("ERROR: Priors were specifyed incorrectly! Use a string defining None, dict or a list in python syntax")
                except:
                    InPriors = self.__convertStrPriors2Dict(priors)
                    if not InPriors:
                        raise Exception("ERROR: Priors were specifyed incorrectly. Use a formated sting. Ex: 'POS:2, NEG:1'")
            else:
                InPriors = priors
            #If priors are defined, they are now a List or a Dict
            if type(InPriors) == dict:
                if len(InPriors) != len(classVar.values) or [x for x in [str(v) for v in classVar.values] if x in InPriors] != [str(v) for v in classVar.values]:
                    raise Exception("Error: Wrong priors: "+str(InPriors.keys())+"\n"+\
                           "       Acepted priors: "+str(classVar.values))
                # Create an empty list of priors
                priorsList = [None]*len(classVar.values)
                for cls_idx,cls_v in enumerate(classVar.values):
                        priorsList[cls_idx] = InPriors[cls_v]
                if getDict:
                    return InPriors
                else:
                    return priorsList
            elif type(InPriors) == list:
                if len(InPriors) != len(classVar.values):
                    raise Exception("ERROR: The number of priors specified are not according to the number of class values.\n"+\
                           "       Available Class values :" + str(classVar.values))
                else:
                    if getDict:
                        priorsDict = {}
                        map(lambda k,v: priorsDict.update({k: v}),[str(x) for x in classVar.values],InPriors)
                        return priorsDict
                    else:
                        return InPriors
            else:
                return None

    def __convertStrPriors2Dict(self,priorStr):
        """Convert a string with priors ex: "POS:2, NEG:1" to the correspondent dictionary.
           Returnes the dictionary or None if there was an error"""
        #Validate and convert the priors
        try:
            priorsDict = {}
            priorsList = priorStr.split(",")
            for prior in priorsList:
                priorEl = prior.strip().split(":")
                if len(priorEl) != 2:
                    return None
                else:
                    priorsDict[priorEl[0]] = float(priorEl[1])
            if priorsDict:
                return priorsDict
            else:
                return None
        except:
            return None


class AZClassifier(object):
    """
    Base Class for all AZClassifiers
    Here we can add methods that are commun to all Classifiers that derivates from this class
    """
    def __new__(cls,name = "AZ classifier", **kwds):
	self = object.__new__(cls)
        self.__dict__ = kwds
        self.examplesFixedLog = {}
        self.name = name
        self.classifier = None
        self.domain = None
        self._isRealProb = False
        self._DFVExtremes = {"min":0, "max":0}  # Store for the Extremes of DFV
        self.nPredictions = 0                    # Number of predictions made with this Classifier
        self.basicStat = None
        self.NTrainEx = 0
        return self
        
    def _updateDFVExtremes(self, DFV):
        if DFV < self._DFVExtremes["min"]:
            self._DFVExtremes["min"] = DFV
        if DFV > self._DFVExtremes["max"]:
            self._DFVExtremes["max"] = DFV

    def isRealProb(self):
        return self._isRealProb

    def getDFVExtremes(self):
        #If the extremes were never set, return None
        if self._DFVExtremes["min"]==0 and self._DFVExtremes["max"] == 0:
            return None
        else:
            return self._DFVExtremes

    def resetCounters(self):
        self._DFVExtremes = {"min":0, "max":0}
        self.nPredictions = 0

    def getNTrainEx(self):
        """Return the number of examples used at Trin time"""
        return self.NTrainEx


    def getTopImportantVars(self, inEx, nVars = 1,gradRef = None):
        """Return the n top important variables (n = nVars) for the given example"""
        varGradVal = []
        varGradName = []
        ExFix = dataUtilities.ExFix()
        ExFix.set_domain(self.domain)
        ex = ExFix.fixExample(inEx)
        if self.basicStat == None or not self.NTrainEx or (self.domain.classVar.varType == orange.VarTypes.Discrete and len(self.domain.classVar.values)!=2):
            return None
        if gradRef == None:
            gradRef = self(ex,returnDFV = True)[1]
        def calcDiscVarGrad(var,ex,gradRef):
            localVarGrad = 0
            localMaxGrad = gradRef
            #Uncomment next line to skip discrete variables
            #return localMaxGrad
            for val in self.domain[var].values:
                localEx = orange.Example(ex)
                localEx[var] = val
                pred = self(localEx,returnDFV = True)[1]
                if abs(gradRef-pred) > localVarGrad:
                    localVarGrad = abs(gradRef-pred)
                    localMaxGrad = pred
            return localMaxGrad


        def calcContVarGrad(var,ex,gradRef):
            localEx = orange.Example(ex)
            localEx[var] = ex[var] + ((self.basicStat[var]["max"]-self.basicStat[var]["min"])/self.getNTrainEx())+1
            ResUp = self(localEx,returnDFV = True)[1]
            #To only use one direction single step, uncomment next line
            return ResUp
            localEx[var] = ex[var] - ((self.basicStat[var]["max"]-self.basicStat[var]["min"])/self.getNTrainEx())+1
            ResDown = self(localEx,returnDFV = True)[1]
            if abs(ResUp-gradRef) > abs(ResDown-gradRef):
                return ResUp
            else:
                return ResDown
 
        for attr in self.domain.attributes:
            varGradName.append(attr.name)
            if attr.varType == orange.VarTypes.Discrete:
                varGradVal.append(abs(gradRef-calcDiscVarGrad(attr.name,ex,gradRef)))
            else:
                varGradVal.append(abs(gradRef-calcContVarGrad(attr.name,ex,gradRef)))
        #Order the vars in terms of importance
        # insertion sort algorithm
        for i in range(1, len(varGradVal)):
            save = varGradVal[i]
            saveName = varGradName[i]
            j = i
            while j > 0 and varGradVal[j - 1] < save:
                varGradVal[j] = varGradVal[j - 1]
                varGradName[j] = varGradName[j - 1]
                j -= 1
            varGradVal[j] = save
            varGradName[j] = saveName
        #print varGradName
        #print varGradVal
        return varGradName[0:min(int(nVars),len(self.domain.attributes))]


