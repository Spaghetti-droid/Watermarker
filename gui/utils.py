import log.LogManager as lm
from typing import Literal

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
    
    x0, x1 = OPS[anchor[0]](anchorX, width)
    y0, y1 = OPS[anchor[1]](anchorY, height)
    
    return ((x0, y0), (x1, y1))

def _sub(p:float, length:int) -> tuple[float, float]:
    return p - length, p

def _add(p:float, length:int) -> tuple[float, float]:
    return p, p + length

def _expand(p:float, length: int) -> tuple[float, float]:
    return p-length/2, p+length/2


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
            ratio = 1 - position - margin
        case 'm':
            if position > 0.5:
                ratio = 2*(1 - position - margin)
            else:
                ratio = 2*(position - margin)
        case 'r' | 'b':
            ratio = position - margin
        case _:
            raise ValueError("Anchor not recognised")
        
    if ratio < 0:
        # Happens when entire shape must stay in margin
        ratio = 0
        
    return ratio    

OPS = {
    't': _add,
    'm': _expand,
    'b': _sub,
    'l': _add,
    'r': _sub
}
