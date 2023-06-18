import re
import os

#WORKING_DIR = os.getcwd()
WORKING_DIR = os.path.dirname(__file__)

#print(f"DEBUG: WD = '{WORKING_DIR}', CWD = '{os.getcwd()}'")

OPTION_PARSING_PATTERN = re.compile(r"\s*((?:\w+\s*\w+)+)\s*=\s*((?:\".*\")|(?:[\d\.]+))")

WATERMARK_FOLDER_NAME = 'Watermarked'
DEFAULT_MARGIN = 0
DEFAULT_RELATIVE_HEIGHT = 0.02
DEFAULT_TEXT_OPACITY = 128
DEFAULT_RELATIVE_STROKE_WIDTH = 0.05
DEFAULT_FONT = 'arial.ttf'

class WMConfig:
    """ Contains all config information for the watermarking process
    """   
    def __init__(self, text:str=None, font:str=DEFAULT_FONT, margin:float=DEFAULT_MARGIN, 
                 rHeight:float=DEFAULT_RELATIVE_HEIGHT, rStrokeWidth:float=DEFAULT_RELATIVE_STROKE_WIDTH, 
                 opacity:float=DEFAULT_TEXT_OPACITY, inDir:str = None, outDir:str=None) -> None:
        self.text = text
        self.font = font
        self.margin = margin
        self.rHeight = rHeight
        self.rStrokeWidth = rStrokeWidth
        self.opacity = opacity
        self.inDir = inDir
        self.outDir = outDir

def toAbsolutePath(path:str) -> str:
    """Converts relative paths to absolute ones

    Args:
        path (str): the path to convert

    Returns:
        str: path if it is already absolute, the absolute version of path otherwise 
    """
    if path.startswith("/"):
        return path
    
    return os.path.join(WORKING_DIR, path)

def parse(matched:re.Match[str], out_config:WMConfig):
    """Extract information from matched and use it to fill out_config

    Args:
        matched (re.Match[str]): The result of matching a file line with OPTION_PARSING_PATTERN
        out_config (WMConfig): [OUTPUT] The config object to fill.
    """
    key = matched.group(1)
    match key:
        case "Text":
            out_config.text = matched.group(2)[1:-1]
        case "Font":
            out_config.font = matched.group(2)[1:-1]
        case "Font Path":
            out_config.font = toAbsolutePath(matched.group(2)[1:-1])
        case "Margin":
            out_config.margin = float(matched.group(2))
        case "Relative Height":
            out_config.rHeight = float(matched.group(2))
        case "Relative Stroke Width":
            out_config.rStrokeWidth = float(matched.group(2))
        case "Opacity":
            out_config.opacity = int(matched.group(2))
        case "Input Folder":
            out_config.inDir = toAbsolutePath(matched.group(2)[1:-1])
        case "Output Folder":
            out_config.outDir = toAbsolutePath(matched.group(2)[1:-1])
        case _:
            print("[[WARNING]] Option not recognised: " + key)
        
def readConfig(path:str) -> WMConfig:
    """Generate a config object using a config file

    Args:
        path (str): The path to the config file

    Returns:
        WMConfig: Generated config object
    """
    with open(path, encoding="utf-8") as f:
        config = WMConfig()
        for line in f:
            matched = re.match(OPTION_PARSING_PATTERN, line)
            if matched:
                parse(matched, config)
    
    return config
                