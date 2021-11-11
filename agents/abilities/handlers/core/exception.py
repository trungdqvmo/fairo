"""
Define exception of ablities
"""

class CapabilityError(NotImplementedError):
    pass

class AbilityError(CapabilityError):
    pass

class NonCapableAbilityError(CapabilityError):
    pass
