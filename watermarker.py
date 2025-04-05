from PIL import UnidentifiedImageError
import os
import sys
import traceback
import logging
import argparse
from pathlib import Path
from glob import glob

import LogManager as lm
import ConfigHandler as ch
from WatermarkerEngine import WatermarkerEngine

# Watermark all images in a folder
# TODO:
#   - GUI
#   - Check image rotation loss is solved 
#   - Cache font size?
#   - Figure out how to handle the default destination
#   - load and save to different config files

logging.basicConfig(format=lm.LOG_FORMAT, filename='Watermarker.log', level=lm.DEFAULT_LOG_LEVEL, filemode='w')
logger = lm.getLogger(__name__)

def main():
    try:
        run()
        print("Done!")
        logger.info("Done")
    except Exception:
        logger.exception('Program terminated due to exception')
        print("Program terminated due to error")
        print("-"*60)
        traceback.print_exc(file=sys.stdout)
        print("-"*60)

def initArgParser(config: ch.WMConfig) -> argparse.Namespace:
    """Defines the arguments that the program can use

    Returns:
        argparse.Namespace: The argument values the user specified to the application
    """
    parser = argparse.ArgumentParser(prog="watermarker.py", 
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='''\
Take a list of files and watermark them
''')
    parser.add_argument("input", type=Path, nargs='*', help="Not saved by --save. Paths to the images that we want to watermark.")
    parser.add_argument("-d", "--destination-folder", dest='outDir', type=Path, help=f"Path to the folder containing where the watermarked pictures should go. Currently: {config.outDir}.", default=config.outDir)
    parser.add_argument("-l", "--log-level", dest="logLevel", help=f"Level of detail for logged events. Currently: {config.logLevel}", default=config.logLevel)
    parser.add_argument("-t", "--text", help=f"Text to use as watermark. Currently: {config.text}.", default=config.text)
    parser.add_argument("-f", "--font",  help=f"Name or path of a font to be used in the watermark. If a name is used, the font must be installed on the system. Currently: {config.font}.", default=config.font)
    parser.add_argument("-m", "--margin", type=float, help=f"Values between 0 and 1. The margin wanted between the watermark and the edge scaled for width and height. Currently: {config.margin}.", default=config.margin)
    parser.add_argument("-S", "--stroke-width", dest='strokeWidth', type=float, help=f"Values between 0 and 1. How thick the stroke should be compared to font size. Currently: {config.rStrokeWidth}.", default=config.rStrokeWidth)
    parser.add_argument("-H", "--height", type=float, help=f"Values between 0 and 1. How high the text should be relative to the image. Currently: {config.rHeight}.", default=config.rHeight)
    parser.add_argument("-O", "--opacity", type=int, help=f"Values between 0 and 255. The opacity of the watermark. 0 is opaque, 255 is transparent. Currently: {config.opacity}.", default=config.opacity)

    parser.add_argument("-s", "--save", action='store_true', help="Save the provided options, so that they become the new defaults.")
    return parser.parse_args()

def run():
    
    args = initArgParser(ch.loadConfig())
    lm.getLogger().setLevel(args.logLevel.upper())
    config = ch.WMConfig.fromArgs(args)
    
    if not configIsValid(config):
        return
    
    if args.save:
        print('Saving config')
        if ch.saveConfig(config):
            print('Save successful!')
        else:
            print('Save failed!')
    
    if not args.input:
        print('No images to watermark')
        logger.info('No images provided')
        return
    
    engine = WatermarkerEngine(config)
    
    print("Watermarking files:")
    logger.info("Watermarking files:")
    
    if os.name == 'nt':
        # Windows doesn't expand wildcards in shell, so we have to do it.
        globs = [ glob(str(p)) for p in args.input]
        args.input = [Path(p) for sub in globs for p in sub]
        logger.debug(f'Input after expanding globs: {args.input}')
    
    for path in args.input:
        print(str(path))
        logger.info('Marking: ' + str(path))
        isImg = True
        if path.is_file():
            try:
                engine.markImage(path)
            except UnidentifiedImageError:
                isImg = False
        else:
            isImg = False
        
        if isImg:
            logger.debug('Success!')
        else:
            print('Not a supported image: ' + str(path))
            logger.warning(f'Not a supported image: {str(path)}')
                
                

def configIsValid(config:ch.WMConfig) -> bool:
    """Check config to make sure all needed information is there

    Args:
        config (WMConfig): The watermarker configuration object

    Returns:
        bool: True if there is no issue, False otherwise
    """
    
    if not config.outDir:
        print("[[SEVERE]] No value for 'Output Folder' provided")
        logger.error("No value for 'Ouput Folder' provided")
        return False 
    
    if not config.text:
        print("[[SEVERE]] No value for 'Text' provided!")
        logger.error("No value for 'Text' provided")
        return False
    
    if not os.path.exists(config.outDir):
        print("[[WARNING]] Output Folder doesn't exist! Creating it at: " + str(config.outDir))
        logger.warning(f"Output folder doesn't exist. Creating it at: {str(config.outDir)}")
        os.mkdir(config.outDir)
        
    return True
    
    
if __name__ == '__main__':
    main()