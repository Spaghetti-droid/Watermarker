from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os

from ConfigHandler import WMConfig

class WatermarkerEngine:
    """ Handles file watermarking
    """
    
    def __init__(self, config:WMConfig) -> None:
        self.config = config
       
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
        config = self.config
        point_size = 0
        font_height = 0
        font_width = 0
        while font_height < target_height and font_width < max_width:
            point_size += 1
            font = ImageFont.truetype(config.font, point_size)
            (x0, y0, x1, y1) = font.getbbox(config.text)
            #font_height = y1-y0
            #font_width = x1-x0
            font_height = y1
            font_width = x1
        
        point_size -= 1
        if point_size == 0:
            raise ValueError('No font size fits the target dimensions!')
        return font

    def markImage(self, img_path:Path) -> None:
        """Watermark the image at img_file

        Args:
            img_file (os.DirEntry[str]): The file containing the image we want to watermark
        """

        config = self.config

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