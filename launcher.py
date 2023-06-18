from PIL import UnidentifiedImageError
import os, sys, traceback

from config_reader import WMConfig, readConfig, WORKING_DIR
from watermarker import Watermarker

# Watermark all images in a folder
# TODO:
#   - GUI
#   - Cmd line version
#   - Solve image rotation loss
#   - Auto save params
#   - Cache font size?

CONFIG_FILE = os.path.join(WORKING_DIR, "config.txt")

def main():
    try:
        run()
        print("Done!")
    except Exception:
        print("Program terminated due to error")
        print("-"*60)
        traceback.print_exc(file=sys.stdout)
        print("-"*60)
        
    
    input("Press enter to quit")

def run():
    
    config = readConfig(CONFIG_FILE)
    
    if not configIsValid(config):
        return
    
    watermarker = Watermarker(config)
    
    print("Watermarking files:")
    
    for file in os.scandir(config.inDir):
        print(file.path)
        if file.is_file():
            try:
                watermarker.markImage(file)
            except UnidentifiedImageError:
                print('Not an image: ' + file.path)
                

def configIsValid(config:WMConfig) -> bool:
    """Check config to make sure all needed information is there

    Args:
        config (WMConfig): The watermarker configuration object

    Returns:
        bool: True if there is no issue, False otherwise
    """
    
    if not config.inDir:
        print("[[SEVERE]] No value for 'Input Folder' provided")
        return False 
    
    if not config.outDir:
        print("[[SEVERE]] No value for 'Output Folder' provided")
        return False 
    
    if not config.text:
        print("[[SEVERE]] No value for 'Text' provided!")
        return False
    
    if not os.path.isdir(config.inDir):
        print('[[SEVERE]] Folder not found: ' + config.inDir)
        return False
    
    if not os.path.exists(config.outDir):
        print("[[WARNING]] Output Folder doesn't exist! Creating it at: " + config.outDir)
        os.mkdir(config.outDir)
        
    return True
    
if __name__ == '__main__':
    main()