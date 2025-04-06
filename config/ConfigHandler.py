from pathlib import Path
from tinydb import TinyDB, Query

import LogManager as lm

import config.Profile as pr
from config.Profile import Profile
from config.Config import Config

CONFIG_FILE_PATH = Path('config.json')

NAME_KEY = 'Name'
TEXT_KEY = 'Text'
FONT_KEY = 'Font'
MARGIN_KEY = 'Margin'
HEIGHT_KEY = 'Height'
STROKE_WIDTH_KEY = 'StrokeWidth'
OPACITY_KEY = 'Opacity'
OUTPUT_KEY = 'OutputFolder'

DEFAULT_PROFILE_KEY = 'DefaultProfile'
LOG_LEVEL_KEY = 'LogLevel'


logger = lm.getLogger(__name__)

db = TinyDB(CONFIG_FILE_PATH)
profiles = db.table('Profiles')
confs = db.table('Configuration')               
   
def saveProfile(profile:Profile) -> bool:
    """Insert or update profile in db
    Args:
        profile (Profile):
    Returns:
        bool: True if success
    """
    try:
        logger.info(f"Saving profile '{profile.name}'")
        Item = Query()
        profiles.upsert({
            NAME_KEY: profile.name,
            TEXT_KEY: profile.text,
            FONT_KEY: profile.font,
            MARGIN_KEY: profile.margin,
            HEIGHT_KEY: profile.rHeight,
            STROKE_WIDTH_KEY: profile.rStrokeWidth,
            OPACITY_KEY: profile.opacity,
            OUTPUT_KEY: str(profile.outDir)
            }, Item[NAME_KEY] == profile.name)
        return True
    except Exception:
        logger.exception('Save Profile failed')
        return False
    
def removeProfiles(names:list) -> bool:
    """Remove all profiles listed from the db
    Args:
        names (list):
    Returns:
        bool: True if success
    """
    try:
        logger.warning(f"Deleting profiles '{names}'")
        Item = Query()
        profiles.remove(Item[NAME_KEY].one_of(names))
        return True
    except Exception:
        logger.exception('Remove profile failed')
        return False 
    
def updateDefaultProfile(name:str) -> None:
    logger.info("Updating default profile")
    confs.update({DEFAULT_PROFILE_KEY: name}, doc_ids=[1])
    
def updateLogLevel(logLevel:str) -> None:
    logger.info("Updating log level")
    confs.update({LOG_LEVEL_KEY: logLevel}, doc_ids=[1])
    
def loadProfile(name:str) -> Profile:
    """Load a profile from the db
    Args:
        name (str): Name of the profile to load
    Returns:
        Profile: A profile or None if it wasn't found
    """
    profiles = loadProfiles([ name ])
    if not profiles:
        logger.warning(f"Couldn't find profile {name} in the db.")
        return None
    return profiles[0]

def loadProfiles(names:str) -> Profile:
    """Load several profiles from db
    Args:
        names (str): Names of the profiles to load
    Returns:
        list[Profile]: All loaded profiles
    """
    logger.info(f"Loading profiles '{names}'")
    Item = Query()
    profileDicts = profiles.search(Item[NAME_KEY].one_of(names))
    return [ toProfile(pDict) for pDict in profileDicts ]

def loadConfig() -> Config:
    """Load config from db, as well as the default profile. 
    If the default profile wasn't found, the hardcoded default will be used
    instead and the loadFailed flag will be set  
    Returns:
        Config:
    """
    logger.info("Loading config")
    # There should only ever be one line in this table
    confDict = confs.all()[0]
    defaultProfileName = confDict[DEFAULT_PROFILE_KEY]
    profile = loadProfile(defaultProfileName)
    if not profile:
        profile = Profile(defaultProfileName, loadFailed=True)
    return Config(profile, defaultProfileName, confDict[LOG_LEVEL_KEY])

def listProfileNames() -> list:
    """Get the names of all profiles in the db
    Returns:
        list:
    """
    logger.info("Listing profiles")
    return [ p[NAME_KEY] for p in profiles.all() ]
    
        
                
def toProfile(profileDict) -> Profile:
    """Convert a json object into a WMConfig
    Args:
        optsAsJson (json): The json to convert
    Returns:
        Options: The options contained in the json
    """
    return Profile(
        name=profileDict[NAME_KEY],
        text=profileDict[TEXT_KEY],
        font=profileDict[FONT_KEY],
        margin=profileDict[MARGIN_KEY],
        rHeight=profileDict[HEIGHT_KEY],
        rStrokeWidth=profileDict[STROKE_WIDTH_KEY],
        opacity=profileDict[OPACITY_KEY],
        outDir=profileDict[OUTPUT_KEY]
    )

# First time setup

if not confs.all():
    logger.warning("Initialising DB")
    confs.insert({DEFAULT_PROFILE_KEY:pr.DEFAULT_NAME, LOG_LEVEL_KEY:lm.DEFAULT_LOG_LEVEL}) 
    if not profiles.all():
        # Do this conditionally as it will allow the program to notice some cases
        # Where the db was corrupted
        logger.warning("Adding default profile to db")
        saveProfile(Profile())
    else:
        logger.error("Existing profiles encountered during initialisation!")