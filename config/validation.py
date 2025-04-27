from config.Profile import Profile
import engine.anchorManagement as am

def checkXYValues(profile: Profile) -> str:
    if _is0To1(profile.xy[0]) and _is0To1(profile.xy[1]):
        return None
    return "Anchor x and y coordinates should be between 0 and 1"

def _is0To1(value) -> bool:
    return value >= 0 and value <= 1

def checkMarginValue(profile: Profile) -> str:
    if profile.margin >= 0.5 or profile.margin < 0:
        return "Margin value should be between 0 and 0.5"
    return None

def checkAnchorPoint(profile: Profile) -> str:
    return am.getAnchorManager(profile).validate()
        