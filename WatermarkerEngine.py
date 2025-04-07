from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

import LogManager as lm
from config.ConfigHandler import Profile

logger = lm.getLogger(__name__)

class WatermarkerEngine:
    """ Handles file watermarking
    """
    
    def __init__(self, profile:Profile) -> None:
        self.profile = profile
        self.maxHeight = 0
        self.maxPt = 0
    
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
        
       
    def getFont(self, target_height:int, max_width:int) -> ImageFont.FreeTypeFont:
        """ Generate a font object, respecting as much as possible the constraints set by the arguments.

        Args:
            target_height (int): The height in pixels we want our font to have
            max_width (int): The limit in pixels on the width of the font

        Raises:
            ValueError: If the font cannot be sized to respect the constraints

        Returns:
            ImageFont.Unbound | ImageFont.FreeTypeFont: a font object
        """
        point_size = self.getInitialPointSize(target_height)
        logger.debug(f"Initial pt size:{point_size}")
        font, font_width, font_height = self.fontAndDimensions(point_size)
        
        if font_height < target_height and font_width < max_width:
            # Font is smaller than allowed, see if it can be bigger
            while font_height < target_height and font_width < max_width:
                point_size += 1
                font, font_width, font_height = self.fontAndDimensions(point_size)
            
            point_size -= 1
        else:
            # Font is bigger than allowed, make it smaller
            while point_size > 0 and (font_height > target_height or font_width > max_width):
                point_size -= 1
                font, font_width, font_height = self.fontAndDimensions(point_size)

        if point_size == 0:
            raise ValueError('No font size fits the target dimensions!')
        
        self.updateCache(point_size, target_height)
        
        logger.debug(f"Final pt size:{point_size}")
        
        return font
    
    def fontAndDimensions(self, point_size:int) -> tuple:
        """Get the font object that corresponds to point_size, as well as its bounding box
        Args:
            point_size (int): Point size of the font

        Returns:
            tuple: Font, width, height
        """
        font = ImageFont.truetype(self.profile.font, point_size)
        (x0, y0, x1, y1) = font.getbbox(self.profile.text)
        #font_height = y1-y0
        #font_width = x1-x0
        return (font, x1, y1)

    def markImage(self, img_path:Path) -> None:
        """Watermark the image at img_file

        Args:
            img_file (os.DirEntry[str]): The file containing the image we want to watermark
        """

        config = self.profile

        #Opening Image
        img = Image.open(img_path)
        exif = img.getexif()
        originalMode = img.mode
        imgIsRGBA = originalMode == "RGBA"
        if not imgIsRGBA:
            img = img.convert("RGBA")
        
        txt_img = Image.new("RGBA", img.size, (255,255,255,0))

        #Creating text and font object
        width, height = img.size
        font = self.getFont(height*config.rHeight, width)

        #Creating draw object
        draw = ImageDraw.Draw(txt_img) 

        #Positioning Text
        strokeWidth = int(config.rStrokeWidth*font.size)
        if strokeWidth <= 0:
            strokeWidth = 1
        x0, y0, x1, y1 = draw.textbbox((0,0), config.text, font, stroke_width=strokeWidth) 
        #x=width - (x1-x0) - width*DEFAULT_MARGIN
        #y=height - (y1-y0) - height*DEFAULT_MARGIN
        x=width - x1 - width*config.margin
        y=height - y1 - height*config.margin

        #Applying text on image via draw object
        draw.text((x, y), config.text, font=font, fill=(255,255,255,config.opacity), stroke_width=strokeWidth, stroke_fill=(0,0,0,config.opacity)) 
        
        composite = Image.alpha_composite(img, txt_img)
        if not imgIsRGBA:
            composite = composite.convert(originalMode)

        #Saving the new image
        composite.save(os.path.join(config.outDir, img_path.name), exif=exif)