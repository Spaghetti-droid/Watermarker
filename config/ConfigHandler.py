import re
from pathlib import Path
from tinydb import TinyDB, Query

import LogManager as lm

import config.Profile as pr
from config.Profile import Profile
from config.Config import Config

OPTION_PARSING_PATTERN = re.compile(r"\s*((?:\w+\s*\w+)+)\s*=\s*((?:\".*\")|(?:[\d\.]+))")

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
if not confs.all():
    confs.insert({DEFAULT_PROFILE_KEY:pr.DEFAULT_NAME, LOG_LEVEL_KEY:lm.DEFAULT_LOG_LEVEL})                
   
def saveProfile(profile:Profile) -> bool:
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
    
def updateDefaultProfile(config:Config) -> None:
    logger.info("Updating default profile")
    Item = Query()
    confs.update({DEFAULT_PROFILE_KEY:config.activeProfile.name}, Item[DEFAULT_PROFILE_KEY].exists())
    
def updateLogLevel(config:Config) -> None:
    logger.info("Updating log level")
    Item = Query()
    confs.update({LOG_LEVEL_KEY:config.logLevel}, Item[LOG_LEVEL_KEY].exists())
    
def loadProfile(name:str) -> Profile:
    logger.info(f"Loading profile '{name}'")
    Item = Query()
    profileDict = profiles.get(Item[NAME_KEY] == name)
    if not profileDict:
        logger.warning(f"Couldn't find profile {name} in the db.")
        return None
    return toProfile(profileDict)

def loadConfig() -> Config:
    logger.info("Loading config")
    # There should only ever be one line in this table
    confDict = confs.all()[0]
    profile = loadProfile(confDict[DEFAULT_PROFILE_KEY])
    if not profile:
        profile = Profile()
    return Config(profile, confDict[LOG_LEVEL_KEY])
    
        
                
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