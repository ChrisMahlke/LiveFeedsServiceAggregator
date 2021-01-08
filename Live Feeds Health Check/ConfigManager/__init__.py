import configparser
import os


class ConfigManager:
    """ 
    Routines for handling the loading and parsing of the config ini file
    """

    def __init__(self, root, file_name):
        """
        :param root: The root directory of the script
        :param file_name: The file name
        """
        # project root
        self.root = root
        # ini file name
        self.file_name = file_name
        # path to ini file
        self.path = os.path.join(self.root, self.file_name)
        # instantiate config parser
        self.parser = configparser.SafeConfigParser()

    def get_config_data(self, config_type):
        """
        Retrieve the data from the ini file sections
        :param config_type:
        :return: Data model with data from the ini file
        """
        sections = self._get_sections_from_ini_file()
        # Prepare the script's input data model from the config file
        if config_type == "items":
            input_data_model = list(map(self._load_item, sections))
        else:
            input_data_model = list(map(self._load_status_code, sections))
        return input_data_model

    def _get_sections_from_ini_file(self):
        """
        :return: The ini file sections
        """
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
