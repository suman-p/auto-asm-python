'''
Created on Jul 15, 2014

@author: P.Suman
'''
import os
import requests
import time
import globalVars
import collections
from ConfigParser import ConfigParser
from xml.etree import ElementTree as et
from copy import deepcopy
from traceback import format_exc
from csv import reader as csvreader


class TestBase:
    """
    Baseclass with all Product Level functions
    """    
    mdParameters = ["device_type","ip_address","device_refid","device_model","device_serviceTag","device_vendor"]    
    nwConfigTypeMap = {"Private LAN":"PRIVATE_LAN(PRLAN)","Public LAN":"PUBLIC_LAN(PBLAN)","Hypervisor Management":"HYPERVISOR_MANAGEMENT(HMT)",
                       "Hypervisor Migration":"HYPERVISOR_MIGRATION(HMG)","PXE":"PXE(PXE)","Fileshare":"FS(FS)"}
    
    nwMapping = {"PXE":"","PRLAN":"","PBLAN":"","HMG":"","HMT":"","FS":"","SANISCSI":"","SANFCOE":"","HCP":""}

    
    def __init__(self):
        """
        Initialization
        """
        self.loadConfig()
        self.loadServices()
    
    
    def readConfig(self,fileName=None, sectionName=None):
        """
        Reads Config File and returns a dictionary 
        """ 
        config_dict = {}
        try:   
            config = ConfigParser()
            if not fileName:
                fileName = globalVars.configFile
            config.read(fileName)
            if sectionName:
                config_dict[sectionName] = dict(config.items(sectionName))
            else:
                for section in config.sections():
                    config_dict[section]=dict(config.items(section))
        except Exception,e:
            print e
        return config_dict
    
    
    def readFile(self, fileName):
        """
        Reads text file and returns string
        """
        with open(fileName,'r') as rfp:
            data = rfp.read()
        return data
    
    
    def readCsvFile(self, fileName, delimiter=","):
        """
        Reads csv file and returns a List with each row as an element
        """
        if os.path.exists(fileName):
            try:
                filehandle = open(fileName, "rU")
                reader = csvreader(filehandle, delimiter=delimiter)
                retlist = []
                for row in reader:
                    if row:
                        retlist.append(row)
                filehandle.close()
                return retlist, True
            except:
                return "ERROR: %s" % str(format_exc()), False
        else:
            return "ERROR: File \"%s\" does not exists." % fileName, False
    
    
    def loadServices(self):
        """
        Description:
            API to get Service Url's from the Services.xml file.
            
        Input:
                
        Output:
            Returns BeautifulStoneSoup element containing Service URL details
              
        """
        
        tree = et.parse(globalVars.serviceUriInfoFile)
        root = tree.getroot()
        
        for child in root.findall('url'):
            globalVars.serviceUriInfo[child.get('name')] = child.get('uri')
    
        
    def loadConfig(self):
        """
        Description:
            API to get Service Url's from the Services.xml file.
            
        Input:
                
        Output:
            Returns BeautifulStoneSoup element containing Service URL details
              
        """
        globalVars.configInfo =  self.readConfig()            
        
    
    def buildUrl(self, feature, id=None):
        """
        Builds a Service Url and Returns 
        """
        basePath = "http://"+  globalVars.configInfo['Appliance']['ip'] + ":" + globalVars.configInfo['Appliance']['port']
        uri = globalVars.serviceUriInfo[feature]
        if id:
            return basePath +  uri + "/" + id
        else:
            return basePath +  uri
    
    
    def convertUTA(self, data):
        """
        Converts Unicode data to ASCII
        """
        if isinstance(data, basestring):
            return str(data)
        elif isinstance(data, collections.Mapping):
            return dict(map(self.convertUTA, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(self.convertUTA, data))
        else:
            return data
    
    
    def getCredentialId(self, featureList, label=""):
        """
        Returns Credentials Id 
        """    
        uri = self.buildUrl("Credential")    
        response = requests.get(uri)
        credentials  = et.fromstring(response.text)
        idInfo = {}
        for credential in credentials:
            for feature in featureList:    
                for creType in credential.findall(feature):
                    if label:
                        creType.find("label").text
                    idInfo[feature] = creType.find("id").text    
        return idInfo
    
    
    def getServerDiscoveryPayload(self, unmanaged=False):
        """
        Returns Server Discovery Payload 
        """
        serverCredentialId = ""
        credentials = self.getCredentialId(["serverCredential"])
        if credentials.has_key("serverCredential"):
            serverCredentialId = credentials["serverCredential"]
        
        payload = self.readFile(globalVars.serverDiscPayload)
        payload = payload.replace("start_ip", globalVars.configInfo["Discovery"]["start_ip"]).replace("end_ip", 
                                globalVars.configInfo["Discovery"]["end_ip"]).replace("default_server_cred_ref", 
                                        serverCredentialId).replace("manage_in_asm", str(unmanaged).lower())
    
        return payload
    
    
    def discoverServer(self):
        """
        Discovers servers within start_ip and end_ip
        """
        uri = self.buildUrl("Discovery")
        postData = self.getServerDiscoveryPayload()
        response = requests.post(uri,data=postData)
        time.sleep(globalVars.defaultWaitTime)
        return response.text
    
    
    def verifyDiscoveryStatus(self, discRequestResult):
        """
        Verify Discovery Status
        """
        discRequest = et.fromstring(discRequestResult)        
        jobId = discRequest.find("id").text        
        uri = self.buildUrl("Discovery", jobId)
        time.sleep(globalVars.defaultWaitTime)
        response = requests.get(uri)
        discStatus = et.fromstring(response.text)        
        status = discStatus.find("status").text
        discoveredDevices = []
        if status.lower() == "success":                        
            for devices in discStatus.findall("DiscoveredDevices"):
                tempdict = {}
                for device in devices:
                    tempdict[device.tag] = device.text
                discoveredDevices.append(tempdict)            
        return discoveredDevices
    
    
    def generateManagedDevicePayload(self, mdCount=1):
        """
        Generates Managed Devices payload
        """
        payload = self.readFile(globalVars.manageDevicePayload)
        deviceList = et.fromstring(payload)        
        for _ in xrange(mdCount-1):
            device = deepcopy(deviceList.find("ManagedDevice"))
            deviceList.append(device)
        iter = 1
        for device in deviceList.findall("ManagedDevice"):               
            for subDevice in device:
                if subDevice.text is not None and subDevice.text in self.mdParameters:      
                    subDevice.text = subDevice.text + str(iter)
            iter += 1                    
        return et.tostring(deviceList, encoding='utf8')
    
    
    def manageDevice(self, discoveredDevices):
        """
        Create Device in Inventory, return array of Managed Devices created
        """
        iter = 1
        payload = self.generateManagedDevicePayload(len(discoveredDevices))
        for device in discoveredDevices:
            payload = payload.replace("device_type"+str(iter), device["deviceType"]).replace("ip_address"+str(iter), 
                        device["ipAddress"]).replace("device_model"+str(iter), device["model"]).replace("device_refid"+str(iter), 
                        device["deviceRefId"]).replace("device_serviceTag"+str(iter),device["serviceTag"]).replace("device_vendor"+str(iter),
                        device["vendor"])
            iter += 1          

        payload = payload.replace('\n','').replace('\t','')
        uri = self.buildUrl("ManagedDevice")       
        response = requests.post(uri,data=payload)
        time.sleep(globalVars.defaultWaitTime)
        return response.text
    
    
    def loadNetwork(self):
        """
        Loads the Network Information provided in Network.csv
        """        
        result, status = self.readCsvFile(globalVars.networkConfig)
        if not status:
            return False
        header = result[0]      
        return [dict(zip(header,result[row])) for row in xrange(1,len(result))]
        
    
    def defineNetwork(self, nwInfo):
        """
        Defines new Network with provided VLAN and Network Type
        """        
        payload = self.readFile(globalVars.networkPayload)
        payload = payload.replace("nw_name", nwInfo["Name"]).replace("nw_desc", 
                                nwInfo["Description"]).replace("nw_type", nwInfo["Type"]).replace(
                                "nw_vlan", nwInfo["VLANID"].replace("nw_static",nwInfo["Static"]))
    
        payload = payload.replace('\n','').replace('\t','')
        uri = self.buildUrl("Network")       
        response = requests.post(uri,data=payload)
        time.sleep(globalVars.defaultWaitTime)
        return response.text
        
    
    def getNetworks(self):
        """
        Get all the Network Information  
        """
        uri = self.buildUrl("Network")    
        response = requests.get(uri)
        return response.json()
    
    
    def manageNetworks(self):
        """
        Create Networks or Manage existing Network        
        """
        networkConfig = self.loadNetwork()
        networks = self.convertUTA(self.getNetworks())        
        for network in networkConfig:
            configKey = self.nwConfigTypeMap[network["Type"]]
            nwMapKey = configKey.split("(")[1][:-1]          
            configKey = configKey.split("(")[0]            
            index = [networks.index(nw) for nw in networks if nw["type"] == configKey]            
            if index: index = index[0] 
            else: index = -1            
            if network["VLANID"] != "":
                if index >= 0 and network["VLANID"] == str(networks[index]["vlanId"]):
                    self.nwMapping[nwMapKey] = networks[index]["id"]
                else:
                    print self.defineNetwork(network)
        print self.nwMapping
    
    
    def createServerPool(self):
        """
        Creates Server Pool with the provided Servers
        """
        
                    
        
        