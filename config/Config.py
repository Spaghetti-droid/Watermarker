import argparse

import LogManager as lm
from config.Profile import Profile



class Config:
    """ Contains all config information for the watermarking process
    """   
    def __init__(self, activeProfile: Profile, logLevel:str=lm.DEFAULT_LOG_LEVEL):
        self.activeProfile = activeProfile
        self.logLevel = logLevel.upper()
        
    @classmethod
    def fromArgs(cls, args:argparse.Namespace):
        
        profile = Profile.fromArgs(args)
        return cls(profile, args.logLevel)
    
    def setActiveProfile(self, profile:Profile):
        self.activeProfile = profile
        
    