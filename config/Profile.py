import argparse
from pathlib import Path

WATERMARK_FOLDER_NAME = 'Watermarked'
DEFAULT_MARGIN = 0
DEFAULT_RELATIVE_HEIGHT = 0.02
DEFAULT_TEXT_OPACITY = 128
DEFAULT_RELATIVE_STROKE_WIDTH = 0.05
DEFAULT_XY = 1, 1
DEFAULT_ANCHOR = 'rb'
DEFAULT_FONT = 'arial.ttf'
DEFAULT_TEXT = '@Watermark'
DEFAULT_NAME = 'Default'

def ifSpecified(value, function):
    if value is not None:
        function(value)
class Profile:
    """ Contains all config information for a watermark
    """   
    def __init__(self, name:str=DEFAULT_NAME, text:str=DEFAULT_TEXT, font:str=DEFAULT_FONT, margin:float=DEFAULT_MARGIN, 
                 rHeight:float=DEFAULT_RELATIVE_HEIGHT, rStrokeWidth:float=DEFAULT_RELATIVE_STROKE_WIDTH, 
                 xy:tuple[float, float]=DEFAULT_XY, anchor:str=DEFAULT_ANCHOR,
                 opacity:float=DEFAULT_TEXT_OPACITY, outDir:str=WATERMARK_FOLDER_NAME, loadFailed:bool = False) -> None:
        self.name = name
        self.text = text
        self.font = font
        self.margin = float(margin)
        self.rHeight = float(rHeight)
        self.rStrokeWidth = float(rStrokeWidth)
        self.xy = float(xy[0]), float(xy[1])
        self.anchor = anchor
        self.opacity = int(opacity)
        if outDir:
            self.outDir = Path(outDir).resolve().absolute()
        # This flag is set when self has been constructed 
        # as a replacement for a non-existing Profile
        self.loadFailed = loadFailed
        self._adjustRHeight()
        
    def merge(self, args:argparse.Namespace):
        """Merge args into self
        Args:
            args (argparse.Namespace):
        """
        # name cannot be edited
        ifSpecified(args.text, self.setText)
        ifSpecified(args.font, self.setFont)
        ifSpecified(args.margin, self._onlySetMargin)
        ifSpecified(args.height, self._onlySetRHeight)
        ifSpecified(args.strokeWidth, self.setRStrokeWidth)
        ifSpecified(args.opacity, self.setOpacity)
        ifSpecified(args.outDir, self.setOutDir)  
        ifSpecified(args.xy, self.setXY)
        ifSpecified(args.anchor, self.setAnchor)
        self._adjustRHeight()      
        
    def setName(self, name:str):
        self.name = name
        
    def setText(self, text:str):
        self.text=text
        
    def setFont(self, font:str):
        self.font = font
    
    def _onlySetMargin(self, margin:float|str):
        self.margin = float(margin)
    
    def setMargin(self, margin:float|str):
        self._onlySetMargin(margin)
        self._adjustRHeight() 
        
    def _onlySetRHeight(self, rHeight:float|str):
        self.rHeight = float(rHeight)
        
    def setRHeight(self, rHeight:float|str):
        self._onlySetRHeight(rHeight)
        self._adjustRHeight() 
        
    def setRStrokeWidth(self, rStrokeWidth:float|str):
        self.rStrokeWidth = float(rStrokeWidth)
    
    def setOpacity(self, opacity:int|str):
        self.opacity = int(opacity)
        
    def setOutDir(self, outDir: str):
        self.outDir = Path(outDir)
        
    def setLoadFailed(self, failed:bool=True):
        self.loadFailed = failed
        
    def setXY(self, xy:tuple[float, float]):
        self.xy = xy
        
    def setAnchor(self, anchor:str):
        self.anchor = anchor
        
    def _adjustRHeight(self):
        """Check if rHeight goes over the max value it can have when accounting for margin, and lower it if it does
        """
        if self.margin is None:
            return
        maxRHeight = 1-2*self.margin
        if self.rHeight > maxRHeight:
            self.rHeight = maxRHeight