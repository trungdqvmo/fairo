import logging

from .exception import *
from .logger import create_ability_logger
from .utils import meta_handler, not_implemented

class BaseHandler(object, metaclass=meta_handler):
    name = None
    def __init__(self, *args, **kwargs):
        self._logger = create_ability_logger(self.name, log_path.joinpath('handlers.log'), self.__capables__)
        self._main_logger = logging.getLogger("main_flow")

    @property
    def logger(self):
        return self._logger

    @property
    def main_logger(self):
        return self._main_logger
