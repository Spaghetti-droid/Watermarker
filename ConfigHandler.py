import re
import argparse
import json
from pathlib import Path

import LogManager as lm

OPTION_PARSING_PATTERN = re.compile(r"\s*((?:\w+\s*\w+)+)\s*=\s*((?:\".*\")|(?:[\d\.]+))")

WATERMARK_FOLDER_NAME = 'Watermarked'
DEFAULT_MARGIN = 0
DEFAULT_RELATIVE_HEIGHT = 0.02
DEFAULT_TEXT_OPACITY = 128
DEFAULT_RELATIVE_STROKE_WIDTH = 0.05
DEFAULT_FONT = 'arial.ttf'
DEFAULT_TEXT = '@Watermark'

CONFIG_FILE_PATH = Path('config.json')

TEXT_KEY = 'Text'
FONT_KEY = 'Font'
MARGIN_KEY = 'MARGIN'
HEIGHT_KEY = 'Height'
STROKE_WIDTH_KEY = 'StrokeWidth'
OPACITY_KEY = 'Opacity'
OUTPUT_KEY = 'OutputFolder'
LOG_LEVEL_KEY = 'LogLevel'

logger = lm.getLogger(__name__)

class WMConfig:
    """ Contains all config information for the watermarking process
    """   
    def __init__(self, text:str=DEFAULT_TEXT, font:str=DEFAULT_FONT, margin:float=DEFAULT_MARGIN, 
                 rHeight:float=DEFAULT_RELATIVE_HEIGHT, rStrokeWidth:float=DEFAULT_RELATIVE_STROKE_WIDTH, 
                 opacity:float=DEFAULT_TEXT_OPACITY, outDir:str=WATERMARK_FOLDER_NAME, logLevel:str=lm.DEFAULT_LOG_LEVEL) -> None:
        self.text = text
        self.font = font
        self.margin = float(margin)
        self.rHeight = float(rHeight)
        self.rStrokeWidth = float(rStrokeWidth)
        self.opacity = int(opacity)
        if outDir:
            self.outDir = Path(outDir).resolve().absolute()
        self.logLevel = logLevel.upper()
        
    @classmethod
    def fromArgs(cls, args:argparse.Namespace):
        return cls(text = args.text, 
            font = args.font, 
            margin = args.margin, 
            rHeight = args.height, 
            rStrokeWidth = args.strokeWidth, 
            opacity = args.opacity, 
            outDir=args.outDir, 
            logLevel=args.logLevel)
        
    def setText(self, text:str):
        self.text=text
        
    def setFont(self, font:str):
        self.font = font
    
    def setMargin(self, margin:float|str):
        self.margin = float(margin)
        
    def setRHeight(self, rHeight:float|str):
        self.rHeight = float(rHeight)
        
    def setRStrokeWidth(self, rStrokeWidth:float|str):
        self.rStrokeWidth = float(rStrokeWidth)
    
    def setOpacity(self, opacity:int|str):
        self.opacity = int(opacity)
        
    def setOutDir(self, outDir: str):
        self.outDir = Path(outDir)
                
                
def toConfig(confAsJson) -> WMConfig:
    """Convert a json object into a WMConfig
    Args:
        optsAsJson (json): The json to convert
    Returns:
        Options: The options contained in the json
    """
    return WMConfig(
        text=confAsJson[TEXT_KEY],
        font=confAsJson[FONT_KEY],
        margin=confAsJson[MARGIN_KEY],
        rHeight=confAsJson[HEIGHT_KEY],
        rStrokeWidth=confAsJson[STROKE_WIDTH_KEY],
        opacity=confAsJson[OPACITY_KEY],
        outDir=confAsJson[OUTPUT_KEY],
        logLevel=confAsJson[LOG_LEVEL_KEY]
    )

def loadConfig() -> WMConfig:
    """ Load config from save file
    Returns:
        Options: Deserialized contents of the file
    """
    if not CONFIG_FILE_PATH.exists():
        logger.info('No save file found, using defaults')
        return WMConfig()
    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            return json.load(f, object_hook=toConfig)
    except Exception as ex:
        print("Error while loading config:", str(ex))
        logger.exception('Error while loading config')
        return WMConfig()

def saveConfig(config:WMConfig) -> bool:
    """Save config to file
    Args:
        config (WMConfig): The config we want to save
    """
    logger.warning('Saving config')
    try:
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump({
                TEXT_KEY: config.text,
                FONT_KEY: config.font,
                MARGIN_KEY: config.margin,
                HEIGHT_KEY: config.rHeight,
                STROKE_WIDTH_KEY: config.rStrokeWidth,
                OPACITY_KEY: config.opacity,
                OUTPUT_KEY: str(config.outDir),
                LOG_LEVEL_KEY: config.logLevel
                }, f, indent=4)
        return True
    except Exception:
        logger.exception('Failed to save config! ')
        return False