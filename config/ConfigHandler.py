from pathlib import Path
from tinydb import TinyDB, Query
import typing

import log.LogManager as lm
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
XY_KEY = 'XY'
ANCHOR_KEY = 'Anchor'

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
            XY_KEY: profile.xy,
            ANCHOR_KEY: profile.anchor,
            OPACITY_KEY: profile.opacity,
            OUTPUT_KEY: str(profile.outDir)
            }, Item[NAME_KEY] == profile.name)
        return True
    except Exception:
        logger.exception('Save Profile failed')
        return False

def removeProfile(name: str) -> bool:
    """Remove the given profile from the db

    Args:
        name (str): profile to delete

    Returns:
        bool: True if success
    """
    return removeProfiles([name])

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

def loadProfiles(names:list[str]) -> list[Profile]:
    """Load several profiles from db
    Args:
        names (list[str]): Names of the profiles to load
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
    
        
                
def toProfile(profileDict: dict, permissive: bool=False) -> Profile:
    """Convert a dict into a Profile
    Args:
        profileDict (dict): The dict to convert
    Returns:
        Profile: The options contained in the dict
    """
    
    getter = _chooseValueGetter(permissive)
    
    return Profile(
        name=getter(profileDict, NAME_KEY, pr.DEFAULT_NAME),
        text=getter(profileDict, TEXT_KEY, pr.DEFAULT_TEXT),
        font=getter(profileDict, FONT_KEY, pr.DEFAULT_FONT),
        margin=getter(profileDict, MARGIN_KEY, pr.DEFAULT_MARGIN),
        rHeight=getter(profileDict, HEIGHT_KEY, pr.DEFAULT_RELATIVE_HEIGHT),
        rStrokeWidth=getter(profileDict, STROKE_WIDTH_KEY, pr.DEFAULT_RELATIVE_STROKE_WIDTH),
        xy=getter(profileDict, XY_KEY, pr.DEFAULT_XY),
        anchor=getter(profileDict, ANCHOR_KEY, pr.DEFAULT_ANCHOR),
        opacity=getter(profileDict, OPACITY_KEY, pr.DEFAULT_TEXT_OPACITY),
        outDir=getter(profileDict, OUTPUT_KEY, pr.WATERMARK_FOLDER_NAME)
    )

def _chooseValueGetter(permissive: bool) -> typing.Callable:
    """Choose between a permissive get-or-default or a more strict get-or-exception
    function for retrieving values from a dictionary

    Args:
        permissive (bool): If True, return function that allows keys to be missing. 
                            Otherwise, return function that raises an error if a key isn't found. 

    Returns:
        typing.Callable: _description_
    """
    if permissive:
        return _permissiveGetter
    
    return _strictGetter    
        
def _permissiveGetter(dic:dict, key:str, default: str):
    return dic.get(key, default)

def _strictGetter(dic:dict, key:str, default: str):
    return dic[key]

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