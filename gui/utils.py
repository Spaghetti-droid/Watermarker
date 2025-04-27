import log.LogManager as lm
from typing import Literal, Callable
from dataclasses import dataclass
from enum import auto, Flag

import engine.anchorManagement as am

logger = lm.getLogger(__name__)

def getCorners(anchorX:float, anchorY:float, width:int, height:int, anchor:str) -> tuple[tuple[float, float], tuple[float, float]]:
    """Get the coordinates of the top left and bottom right corners of the watermark limits

    Args:
        anchorX (float): x position of the anchor point
        anchorY (float): y position of the anchor point
        width (int): width of the rectangle
        height (int): height of the rectangle
        anchor (str): string designating the position of the anchor (eg 'rb')

    Returns:
        tuple[tuple[float, float], tuple[float, float]]: ((x0, y0), (x1, y1))
    """
    
    logger.debug(f"Getting corners for [anchorX: {anchorX}, anchorY: {anchorY}, width: {width}, height: {height}, anchor: {anchor}]")
    
    x0, x1 = OPS[anchor[0]].getCorners(anchorX, width)
    y0, y1 = OPS[anchor[1]].getCorners(anchorY, height)
        
    return ((x0, y0), (x1, y1))

def getRatio(position: float, margin:float, anchorChar:Literal['b', 'l', 'm', 'r', 't']) -> float:
    """ Get the ratio of width/height that the watermark can take up at maximum 

    Args:
        position (float): value of x or y
        margin (float):
        anchorChar (Literal[&#39;b&#39;, &#39;l&#39;, &#39;m&#39;, &#39;r&#39;, &#39;t&#39;]): An anchor character value.

    Raises:
        ValueError: If an unknown character was supplied

    Returns:
        float: max length the watermark can have in the current dimension
    """
    ratio = OPS[anchorChar].getRatio(position, margin)        
    if ratio < 0:
        # Happens when entire shape must stay in margin
        ratio = 0
        
    return ratio 


class Side(Flag):
    """Represents a side of the canvas
    """
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    ALL = TOP | BOTTOM | LEFT | RIGHT

def needMargin(anchorChar:str, marginSide: Side) -> bool:
    """Check whether the current anchor respects the margin on the given side of the canvas

    Args:
        anchor (str)
        marginSide (Side): The side of the canvas the margin is on

    Returns:
        bool: True if the margin is needed, false otherwise
    """
    return OPS[anchorChar].needMargin(marginSide)

def _sub(p:float, length:int) -> tuple[float, float]:
    return p - length, p

def _add(p:float, length:int) -> tuple[float, float]:
    return p, p + length

def _expand(p:float, length: int) -> tuple[float, float]:
    return p-length/2, p+length/2

@dataclass
class AnchorGUIOp:
    """Holds functions needed for a specific anchor type
    """
    getCorners: Callable
    getRatio: Callable
    marginsNeeded: Side
    
    def needMargin(self, marginSide:Side) -> bool:
        return marginSide in self.marginsNeeded

OPS = {
    't': AnchorGUIOp(_add, am.maxRatioLT, Side.BOTTOM),
    'm': AnchorGUIOp(_expand, am.maxRatioM, Side.ALL),
    'b': AnchorGUIOp(_sub, am.maxRatioRB, Side.TOP),
    'l': AnchorGUIOp(_add, am.maxRatioLT, Side.RIGHT),
    'r': AnchorGUIOp(_sub, am.maxRatioRB, Side.LEFT)
} 
