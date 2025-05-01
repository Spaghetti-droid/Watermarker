# Simple script that patches json database by loading existing profiles 
# and saving them with defaults for missing values

import config.ConfigHandler as ch
from config.ConfigHandler import profiles
import log.LogManager as lm

logger = lm.getLogger(__name__)

try:
    for profileDict in profiles:
        profile = ch.toProfile(profileDict, True)
        if not ch.saveProfile(profile):
            raise ValueError("Couldn't save updated profile!")
except Exception:
    logger.exception("Patch failed")