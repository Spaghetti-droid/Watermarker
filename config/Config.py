import argparse

import log.LogManager as lm
from config.Profile import Profile, ifSpecified

class Config:
    """ Contains all config information for the watermarking process
    """   
    def __init__(self, activeProfile: Profile, defaultProfileName:str, logLevel:str=lm.DEFAULT_LOG_LEVEL):
        self.activeProfile = activeProfile
        self.defaultProfileName = defaultProfileName
        self.logLevel = logLevel.upper()
    
    def merge(self, args:argparse.Namespace):
        """Merge args into self
        Args:
            args (argparse.Namespace):
        """
        self.activeProfile.merge(args)
        ifSpecified(args.logLevel, self.setLogLevel)
        ifSpecified(args.defaultProfile, self.setDefaultProfileName)
    
    def setActiveProfile(self, profile:Profile):
        self.activeProfile = profile
        
    def setLogLevel(self, level:str):
        self.logLevel = level.upper()
        
    def setDefaultProfileName(self, name:str):
        self.defaultProfileName = name
        
    