import logging
from .exception import *

class meta_handler(type):
    def __new__(metacls, name, bases, attrs):
        newclass = super().__new__(metacls, clsname, bases, attrs)
        newclass.__abilities__ = []
        newclass.__capables__ = []
        for attr_name, attr in attrs.items():
            # check if attribute is not private nor protected, and check if attribute is method
            if not attr_name.startswith("_") and callable(attr):
                newclass.__abilities__.append(attr_name)
                if attr.__name__ != 'non_capable':
                    newclass.__capables__.append(attr_name)
        return newclass

def not_implemented(func):
    def non_capable(*args, **kwargs):
        raise NonCapableAbilityError()
    return non_capable
