VERSION = "1.0.0"

import configparser
import os, stat
import pathlib
import json

class ConfigManager:
    """ 
    Routines for handling the loading and parsing of the config ini file 
    
    Attributes
    ----------
    None

    Methods
    -------
    getConfigData(configType)
        Retreived the config data

    _getSectionsFromIniFile(self)
        Parse the sections of the ini file

    _loadItem(self, section: str = "")
        Use the section name as the unique identifier (key)

    _loadStatusCode(self, section: str = "")
        TODO
    """

    def __init__(self, root, fileName):     
        # project root
        self.root = root
        # ini file name
        self.fileName = fileName
        # path to ini file
        self.path = os.path.join(self.root, self.fileName)
        # instantiate config parser
        self.parser = configparser.SafeConfigParser()

    def getConfigData(self, configType):
        """ """
        sections = self._getSectionsFromIniFile()
        # Prepare the script's input data model from the config file
        if configType == "items":
            inputDataModel = list(map(self._loadItem, sections))
        else:
            inputDataModel = list(map(self._loadStatusCode, sections))
        return inputDataModel

    def _getSectionsFromIniFile(self):
        """ """
        # read in config file
        self.parser.read(self.path)
        # read in sections
        sections = self.parser.sections()
        return sections

    def _loadItem(self, section: str = "") -> dict:
        details_dict = dict(self.parser.items(section))
        details_dict.update({
            "id": section
        })
        return details_dict

    def _loadStatusCode(self, section: str = "") -> dict:
        details_dict = dict(self.parser.items(section))
        details_dict.update({
            "code": section
        })
        return details_dict