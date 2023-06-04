from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import os

testPath = 'C:/Test/Path'
testText = 'Watermark'

WATERMARK_FOLDER_NAME = 'Watermarked'
DEFAULT_MARGIN = 0.02
DEFAULT_RELATIVE_HEIGHT = 0.02
DEFAULT_TEXT_OPACITY = 128
DEFAULT_STROKE_WIDTH = 4

def main():
    destDir = os.path.join(testPath, WATERMARK_FOLDER_NAME)
    if not os.path.exists(destDir):
        os.mkdir(destDir)
    for file in os.scandir(testPath):
        print(file.path)
        if file.is_file():
            try:
                markImage(file, destDir, testText)
            except UnidentifiedImageError:
                print('Not an image: ' + file.path)
    
    

def markImage(img_file: os.DirEntry[str], dest_dir_path: str, text: str):

    #Opening Image
    img = Image.open(img_file.path).convert("RGBA")
    
    txt_img = Image.new("RGBA", img.size, (255,255,255,0))

    #Creating text and font object
    width, height = img.size
    font = getFont(height*DEFAULT_RELATIVE_HEIGHT, width, text)

    #Creating draw object
    draw = ImageDraw.Draw(txt_img) 

    #Positioning Text
    x0, y0, x1, y1 = draw.textbbox((0,0), text, font, stroke_width=DEFAULT_STROKE_WIDTH) 
    x=width - (x1-x0) - width*DEFAULT_MARGIN
    y=height - (y1-y0) - height*DEFAULT_MARGIN

    #Applying text on image via draw object
    draw.text((x, y), text, font=font, fill=(255,255,255,DEFAULT_TEXT_OPACITY), stroke_width=DEFAULT_STROKE_WIDTH, stroke_fill=(0,0,0,DEFAULT_TEXT_OPACITY)) 
    
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