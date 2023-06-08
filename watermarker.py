from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import os

# Watermark all images in a folder
# TODO:
#   - GUI
#   - Package as exe
#   - Cmd line version
#   - Watermark in prism font
#   - Solve image rotation loss
#   - Auto save params
#   - Cache font size?

workingDir = os.path.dirname(__file__)
testPath = os.path.join(workingDir, 'ToWatermark')
testFont = os.path.join(workingDir, 'fonts/Prism-Regular.otf')
testWMText = '@WATERMARKED'

WATERMARK_FOLDER_NAME = 'Watermarked'
DEFAULT_MARGIN = 0
DEFAULT_RELATIVE_HEIGHT = 0.02
DEFAULT_TEXT_OPACITY = 128
DEFAULT_RELATIVE_STROKE_WIDTH = 0.05

def main():
    if not os.path.isdir(testPath):
        print('Directory not found: ' + testPath)
        return
    
    destDir = os.path.join(testPath, WATERMARK_FOLDER_NAME)
    if not os.path.exists(destDir):
        os.mkdir(destDir)
    for file in os.scandir(testPath):
        print(file.path)
        if file.is_file():
            try:
                markImage(file, destDir, testWMText)
            except UnidentifiedImageError:
                print('Not an image: ' + file.path)
    
    

def markImage(img_file: os.DirEntry[str], dest_dir_path: str, text: str):

    #Opening Image
    img = Image.open(img_file.path).convert("RGBA")
    
    txt_img = Image.new("RGBA", img.size, (255,255,255,0))

    #Creating text and font object
    width, height = img.size
    font = getFont(height*DEFAULT_RELATIVE_HEIGHT, width, text, testFont)

    #Creating draw object
    draw = ImageDraw.Draw(txt_img) 

    #Positioning Text
    strokeWidth = int(DEFAULT_RELATIVE_STROKE_WIDTH*font.size)
    if strokeWidth <= 0:
        strokeWidth = 1
    x0, y0, x1, y1 = draw.textbbox((0,0), text, font, stroke_width=strokeWidth) 
    #x=width - (x1-x0) - width*DEFAULT_MARGIN
    #y=height - (y1-y0) - height*DEFAULT_MARGIN
    x=width - x1 - width*DEFAULT_MARGIN
    y=height - y1 - height*DEFAULT_MARGIN

    #Applying text on image via draw object
    draw.text((x, y), text, font=font, fill=(255,255,255,DEFAULT_TEXT_OPACITY), stroke_width=strokeWidth, stroke_fill=(0,0,0,DEFAULT_TEXT_OPACITY)) 
    
    composite = Image.alpha_composite(img, txt_img).convert("RGB")

    #Saving the new image
    composite.save(os.path.join(dest_dir_path, img_file.name))
    
def getFont(target_height:int, max_width:int, txt:str, name:str = 'arial.ttf'):
    point_size = 0
    font_height = 0
    font_width = 0
    while font_height < target_height and font_width < max_width:
        point_size += 1
        font = ImageFont.truetype(name, point_size)
        (x0, y0, x1, y1) = font.getbbox(txt)
        font_height = y1-y0
        font_width = x1-x0
    
    point_size -= 1
    if point_size == 0:
        raise ValueError('No font size fits the target dimensions!')
    return font
        
    
if __name__ == '__main__':
    main()