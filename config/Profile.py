import argparse
from pathlib import Path

WATERMARK_FOLDER_NAME = 'Watermarked'
DEFAULT_MARGIN = 0
DEFAULT_RELATIVE_HEIGHT = 0.02
DEFAULT_TEXT_OPACITY = 128
DEFAULT_RELATIVE_STROKE_WIDTH = 0.05
DEFAULT_FONT = 'arial.ttf'
DEFAULT_TEXT = '@Watermark'
DEFAULT_NAME = 'Default'

def ifSpecified(value, function):
    if value:
        function(value)
class Profile:
    """ Contains all config information for a watermark
    """   
    def __init__(self, name:str=DEFAULT_NAME, text:str=DEFAULT_TEXT, font:str=DEFAULT_FONT, margin:float=DEFAULT_MARGIN, 
                 rHeight:float=DEFAULT_RELATIVE_HEIGHT, rStrokeWidth:float=DEFAULT_RELATIVE_STROKE_WIDTH, 
                 opacity:float=DEFAULT_TEXT_OPACITY, outDir:str=WATERMARK_FOLDER_NAME) -> None:
        self.name = name
        self.text = text
        self.font = font
        self.margin = float(margin)
        self.rHeight = float(rHeight)
        self.rStrokeWidth = float(rStrokeWidth)
        self.opacity = int(opacity)
        if outDir:
            self.outDir = Path(outDir).resolve().absolute()
        
        
    @classmethod
    def fromArgs(cls, args:argparse.Namespace):
        return cls(name = args.profile,
            text = args.text, 
            font = args.font, 
            margin = args.margin, 
            rHeight = args.height, 
            rStrokeWidth = args.strokeWidth, 
            opacity = args.opacity, 
            outDir=args.outDir)
        
    def merge(self, args:argparse.Namespace):
        # name cannot be changed
        ifSpecified(args.text, self.setText)
        ifSpecified(args.font, self.setFont)
        ifSpecified(args.margin, self.setMargin)
        ifSpecified(args.height, self.setRHeight)
        ifSpecified(args.strokeWidth, self.setRStrokeWidth)
        ifSpecified(args.opacity, self.setOpacity)
        ifSpecified(args.outDir, self.setOutDir)        
        
    def setName(self, name:str):
        self.name = name
        
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