from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from pathlib import Path
import os

import log.LogManager as lm
import engine.anchorManagement as am
from config.ConfigHandler import Profile

logger = lm.getLogger(__name__)

class LoadFontError(Exception):
    """ Exception raised when the font failed to load
    """
    pass

class WatermarkerEngine:
    """ Handles file watermarking
    """
    
    def __init__(self, profile:Profile) -> None:
        self.profile = profile
        self.maxHeight = 0
        self.maxPt = 0
        self.anchorManager = am.getAnchorManager(profile)
    
    def getInitialPointSize(self, target_height:int) -> int:
        """Find the starting point that we'll use in our search for the best font size
        Args:
            target_height (int): The required height of the watermark
        Returns:
            int: A point size
        """
        if not self.maxPt:
            return 1
        
        # This is an extremely simple linear interpolation
        # It seems to work well. 
        # It ignores max_width, though, so a set of images that are too narrow
        # for their watermark might take longer to process 
        return int(target_height * self.maxPt/self.maxHeight)
    
    def updateCache(self, point_size:int, target_height:int):
        """Update cache with the newly obtained point size
        Args:
            point_size (int): Best font size for this image
            target_height (int): The height that was asked for originally
        """
        if self.maxPt < point_size:
            self.maxPt = point_size
            self.maxHeight = target_height
        
       
    def getFont(self, target_height:int, max_width:int, draw:ImageDraw.ImageDraw) -> tuple:
        """ Generate a font object, respecting as much as possible the constraints set by the arguments.

        Args:
            target_height (int): The height in pixels we want our font to have
            max_width (int): The limit in pixels on the width of the font
            draw (ImageDraw.ImageDraw)

        Raises:
            ValueError: If the font cannot be sized to respect the constraints

        Returns:
            tuple[ImageFont.Unbound | ImageFont.FreeTypeFont, int]: a font object, stroke width
        """
        point_size = self.getInitialPointSize(target_height)
        logger.debug(f"Initial pt size:{point_size}")
        font, strokeWidth, font_width, font_height = self.fontAndDimensions(point_size, draw)
        
        if font_height < target_height and font_width < max_width:
            # Font is smaller than allowed, see if it can be bigger
            while font_height < target_height and font_width < max_width:
                point_size += 1
                font, strokeWidth, font_width, font_height = self.fontAndDimensions(point_size, draw)
            
            point_size -= 1
        else:
            # Font is bigger than allowed, make it smaller
            while point_size > 0 and (font_height > target_height or font_width > max_width):
                point_size -= 1
                font, strokeWidth, font_width, font_height = self.fontAndDimensions(point_size, draw)

        if point_size == 0:
            raise ValueError('No font size fits the target dimensions!')
        
        self.updateCache(point_size, target_height)
        
        logger.debug(f"Final pt size:{point_size}")
        
        return font, strokeWidth
    
    def fontAndDimensions(self, point_size:int, draw:ImageDraw.ImageDraw) -> tuple:
        """Get the font object that corresponds to point_size, as well as its dimensions
        
        Args:
            point_size (int): Point size of the font
            draw (ImageDraw.ImageDraw)

        Returns:
            tuple: Font, strokewidth, width, height
        """
        try:
            font = ImageFont.truetype(self.profile.font, point_size)
        except Exception as e:
            logger.exception(f"Couldn't load font: {self.profile.font}")
            raise LoadFontError(f"Couldn't load font: {self.profile.font}") from e
            
            
        strokeWidth = int(self.profile.rStrokeWidth*font.size)
        if strokeWidth <= 0:
            strokeWidth = 1
        x0, y0, x1, y1 = draw.textbbox((0,0), self.profile.text, font, stroke_width=strokeWidth) 
        font_height = y1-y0
        font_width = x1-x0
        return (font, strokeWidth, font_width, font_height)

    def markImage(self, img_path:Path) -> tuple:
        """Load, watermark, and return the marked image
        Args:
            img_path (Path): Path to the image to mark
        Returns:
            tuple: Image, exif data
        """
        
        profile = self.profile

        #Opening Image
        try:
            img = Image.open(img_path)
        except UnidentifiedImageError as e:
            logger.exception(f"Couldn't open image at {str(img_path)}")
            raise ValueError("Couldn't open image") from e
            
        exif = img.getexif()
        originalMode = img.mode
        imgIsRGBA = originalMode == "RGBA"
        if not imgIsRGBA:
            img = img.convert("RGBA")
        
        txt_img = Image.new("RGBA", img.size, (255,255,255,0))

        #Creating draw object
        draw = ImageDraw.Draw(txt_img) 

        #Creating text and font object
        width, height = img.size
        maxWidth, targetHeight = self.anchorManager.getTargetDimensions(width, height)
        font, strokeWidth = self.getFont(targetHeight, maxWidth, draw)

        #Applying text on image via draw object
        logger.debug(f"maxWidth: {maxWidth}/{width}, targetHeight:{targetHeight}/{height}, anchor:{profile.anchor}, xy:{profile.xy}, margin:{profile.margin}")
        x = self.anchorManager.shiftX(width*profile.xy[0], strokeWidth)
        y = self.anchorManager.shiftY(height*profile.xy[1], strokeWidth)       
        draw.text((x,y), profile.text, font=font, fill=(255,255,255,profile.opacity), stroke_width=strokeWidth, stroke_fill=(0,0,0,profile.opacity), anchor=profile.anchor) 
        
        composite = Image.alpha_composite(img, txt_img)
        if not imgIsRGBA:
            composite = composite.convert(originalMode)
        
        return composite, exif

    def _getTargetDimensions(self, width:int, height:int) -> tuple:
        """Get font target height and max width based on image dimensions
        Args:
            width (int): image width
            height (int): image height

        Returns:
            tuple: maxWidth, targetHeight
        """
        maxWidth = width*(1-2*self.profile.margin)
        targetHeight = height*self.profile.rHeight
        return maxWidth, targetHeight
            
    
    def markAndSaveImage(self, img_path:Path) -> None:
        """Watermark the image at img_file

        Args:
            img_file (os.DirEntry[str]): The file containing the image we want to watermark
        """

        composite, exif = self.markImage(img_path)

        #Saving the new image
        composite.save(os.path.join(self.profile.outDir, img_path.name), exif=exif)