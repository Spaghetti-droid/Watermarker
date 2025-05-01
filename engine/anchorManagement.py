from abc import ABC, abstractmethod
from typing import Literal

import log.LogManager as lm
from config.ConfigHandler import Profile

logger = lm.getLogger(__name__)

MARGIN_HIDES_WATERMARK_MESSAGE = "Margin hides watermark!"    

# Max ratio functions 

def maxRatioLT(position: float, margin:float) -> float:
    return 1 - position - margin

def maxRatioRB(position: float, margin:float) -> float:
    return position - margin

def maxRatioM(position: float, margin:float) -> float:
    if position > 0.5:
        return 2*maxRatioLT(position, margin)
    return 2*maxRatioRB(position, margin)

# Functions for gui

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
    
    x0, x1 = OPS[anchor[0]](anchorX, width)
    y0, y1 = OPS[anchor[1]](anchorY, height)
        
    return ((x0, y0), (x1, y1))

def _sub(p:float, length:int) -> tuple[float, float]:
    return p - length, p

def _add(p:float, length:int) -> tuple[float, float]:
    return p, p + length

def _expand(p:float, length: int) -> tuple[float, float]:
    return p-length/2, p+length/2

OPS = {
    't': _add,
    'm': _expand,
    'b': _sub,
    'l': _add,
    'r': _sub
}

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
    match anchorChar:
        case 'l' | 't':
            ratio = maxRatioLT(position, margin)
        case 'm':
            ratio = maxRatioM(position, margin)
        case 'r' | 'b':
            ratio = maxRatioRB(position, margin)
        case _:
            raise ValueError("Anchor not recognised")
        
    if ratio < 0:
        # Happens when entire shape must stay in margin
        ratio = 0
        
    return ratio    

# Single dimension managers

class _DimensionManager(ABC):
    """Base class for the classes that are repsonsible
    for making calculations that take anchor values into account
    """
    def __init__(self, point:float, margin:float):
        self._point = point
        self._margin = margin
        self._maxRatio = self._calcMaxRatio()
        logger.debug(f"Max ratio: {self.maxRatio}")
    
    @abstractmethod
    def _calcMaxRatio(self) -> float:
        """Calculate the maximum size available to a watermark in this dimensions
        (eg max height or max width)
        
        Returns:
            float: A value between 0 and 1 which corresponds to the maximum ratio of width/height that is allowed
        """
        pass
    
    @abstractmethod
    def shift(self, p0:float, strokeWidth:int) -> float:
        """Shift p0 by strokeWidth such that the anchor point is on the edge of the stroke, if necessary

        Args:
            p0 (float): original value of x or y
            strokeWidth (int): number of pixels to shift

        Returns:
            float: shifted p0
        """
        pass
    
    def validate(self) -> str:
        """Check whether margin hides the anchor point
        
        Returns:
            str: None if anchor point isn't hidden, or an error string
        """
        if self._marginHidesWM():
            return MARGIN_HIDES_WATERMARK_MESSAGE
        return None
            
    def _marginHidesWM(self):
        return self._maxRatio <= 0
    
    def maxRatio(self) -> float:
        return self._maxRatio
    
class _RBManager(_DimensionManager):
    """Handles anchor points r and b
    """
    def _calcMaxRatio(self):
        return maxRatioRB(self._point, self._margin)
    
    def shift(self, p0:float, strokeWidth:int) -> float:
        return p0 - strokeWidth
        
    
class _LTManager(_DimensionManager):
    """Handles anchor points l and t
    """  
    def _calcMaxRatio(self):
        return maxRatioLT(self._point, self._margin)
    
    def shift(self, p0:float, strokeWidth:int) -> float:
        return p0 + strokeWidth
    
    
class _MManager(_DimensionManager):
    """Handles anchor points m in either dimension
    """
    def _calcMaxRatio(self):
        return maxRatioM(self._point, self._margin)
        
    def shift(self, p0:float, strokeWidth:int) -> float:
        return p0
 
# Main manager class 
   
class _AnchorManager:
    """ Handles any operation that needs to take an anchor into account
    """
    def __init__(self, profile:Profile):
        self.widthManager = _chooseWidthManager(profile)
        self.heightManager = _chooseHeightManager(profile)
        self.rHeight = profile.rHeight
        maxRHeight = self.heightManager.maxRatio()
        if self.rHeight > maxRHeight:
            logger.debug(f"rHeight limited to {maxRHeight}")
            self.rHeight = maxRHeight       
        
    def getTargetDimensions(self, imgWidth:int, imgHeight:int) -> tuple[float, float]:
        """ Get target height and max width for the current watermark
        
        Args:
            imgWidth (int): Width of the image to watermark
            imgHeight (int): Height of the image to watermark

        Returns:
            tuple[float, float]: maxWidth, targetHeight
        """
        maxWidth = imgWidth*self.widthManager.maxRatio()
        targetHeight = imgHeight*self.rHeight
        return maxWidth, targetHeight
    
    def validate(self) -> str:
        """Check whether margin hides the anchor point
        
        Returns:
            str: None if anchor point isn't hidden, or an error string
        """
        return self.heightManager.validate() or self.widthManager.validate()
    
    def shiftX(self, x0:float, strokeWidth:int) -> float:
        """Shift x by strokeWidth such that the anchor point is on the edge of the stroke, if necessary

        Args:
            x0 (float): original value of x
            strokeWidth (int): number of pixels to shift

        Returns:
            float: shifted x
        """
        return self.widthManager.shift(x0, strokeWidth)
    
    def shiftY(self, y0:float, strokeWidth:int) -> float:
        """Shift y by strokeWidth such that the anchor point is on the edge of the stroke, if necessary

        Args:
            x0 (float): original value of y
            strokeWidth (int): number of pixels to shift

        Returns:
            float: shifted y
        """
        return self.heightManager.shift(y0, strokeWidth)
   
# Manager choice
    
def _chooseWidthManager(profile:Profile) -> _DimensionManager:
    """Choose the appropriate dimension manager for the x direction
    Args:
        profile (Profile)

    Raises:
        ValueError: If the anchor value isn't recognised

    Returns:
        _DimensionManager: The object that handles the current x-dimension anchor type
    """
    xAnchor = profile.anchor[0]
    match xAnchor:
        case 'l':
            return _LTManager(profile.xy[0], profile.margin)
        case 'm':
            return _MManager(profile.xy[0], profile.margin)
        case 'r':
            return _RBManager(profile.xy[0], profile.margin)
        case _:
            raise ValueError(f"'{xAnchor}' is not a recognised anchor for the x direction")
        
def _chooseHeightManager(profile:Profile) -> _DimensionManager:
    """Choose the appropriate dimension manager for the y direction
    Args:
        profile (Profile)

    Raises:
        ValueError: If the anchor value isn't recognised

    Returns:
        _DimensionManager: The object that handles the current y-dimension anchor type
    """
    yAnchor = profile.anchor[1]
    match yAnchor:
        case 't':
            return _LTManager(profile.xy[1], profile.margin)
        case 'm':
            return _MManager(profile.xy[1], profile.margin)
        case 'b':
            return _RBManager(profile.xy[1], profile.margin)
        case _:
            raise ValueError(f"'{yAnchor}' is not a recognised anchor for the y direction")
        
# AM singleton handling

_anchorManagerSoleInstance = None
def getAnchorManager(profile:Profile) -> _AnchorManager:
    """Get the anchor manager singleton. The singleton is instanciated if it doesn't exist yet.

    Args:
        profile (Profile)

    Returns:
        _AnchorManager: The object that handles all operations that take the anchor settings into account
    """
    if _anchorManagerSoleInstance:
        return _anchorManagerSoleInstance
    return _AnchorManager(profile)
