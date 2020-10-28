import configparser
import os

VERSION = "1.0.0"


class ConfigManager:
    """ 
    Routines for handling the loading and parsing of the config ini file

    Methods
    -------
    getConfigData(configType)
        Retrieved the config data

    _getSectionsFromIniFile(self)
        Parse the sections of the ini file

    _loadItem(self, section: str = "")
        Use the section name as the unique identifier (key)

    _loadStatusCode(self, section: str = "")
        TODO
    """

    def __init__(self, root, file_name):
        # project root
        self.root = root
        # ini file name
        self.file_name = file_name
        # path to ini file
        self.path = os.path.join(self.root, self.file_name)
        # instantiate config parser
        self.parser = configparser.SafeConfigParser()

    def get_config_data(self, config_type):
        """ """
        sections = self._get_sections_from_ini_file()
        # Prepare the script's input data model from the config file
        if config_type == "items":
            config_item_data = list(map(self._load_item, sections))
        else:
            config_item_data = list(map(self._load_status_code, sections))
        return config_item_data

    def _get_sections_from_ini_file(self):
        """ """
        # read in config file
        self.parser.read(self.path)
        # read in sections
        sections = self.parser.sections()
        return sections

    def _load_item(self, section: str = "") -> dict:
        details_dict = dict(self.parser.items(section))
        details_dict.update({
            "id": section
        })
        return details_dict

    def _load_status_code(self, section: str = "") -> dict:
        details_dict = dict(self.parser.items(section))
        details_dict.update({
            "code": section
        })
        return details_dict
