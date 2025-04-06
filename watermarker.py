from PIL import UnidentifiedImageError
import os
import sys
import traceback
import logging
import argparse
from pathlib import Path
from glob import glob

import LogManager as lm
import config.ConfigHandler as ch
from config.Config import Config
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
    except Exception:
        logger.exception('Program terminated due to exception')
        print("Program terminated due to error")
        print("-"*60)
        traceback.print_exc(file=sys.stdout)
        print("-"*60)

def initArgParser(config: Config) -> argparse.Namespace:
    """Defines the arguments that the program can use

    Returns:
        argparse.Namespace: The argument values the user specified to the application
    """
    parser = argparse.ArgumentParser(prog="watermarker.py", 
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='''\
Take a list of files and watermark them
''')
    profile = config.activeProfile
    parser.add_argument("input", type=Path, nargs='*', help="Not saved by --save. Paths to the images that we want to watermark.")
    parser.add_argument("--log-level", dest="logLevel", help=f"Level of detail for logged events. Currently: {config.logLevel}", default=config.logLevel)
    parser.add_argument("-p", "--profile", help=f"Name of an existing profile to use as a default for watermark options. Currently: {profile.name}")

    wmGroup = parser.add_argument_group('Watermarking Profile', 'All options that can be saved in a profile. Most of these affect the appearance of the watermark in some way')

    wmGroup.add_argument("-d", "--destination-folder", dest='outDir', type=Path, help=f"Path to the folder containing where the watermarked pictures should go. Currently: {profile.outDir}.")
    wmGroup.add_argument("-t", "--text", help=f"Text to use as watermark. Currently: {profile.text}.")
    wmGroup.add_argument("-f", "--font",  help=f"Name or path of a font to be used in the watermark. If a name is used, the font must be installed on the system. Currently: {profile.font}.")
    wmGroup.add_argument("-m", "--margin", type=float, help=f"Values between 0 and 1. The margin wanted between the watermark and the edge scaled for width and height. Currently: {profile.margin}.")
    wmGroup.add_argument("-S", "--stroke-width", dest='strokeWidth', type=float, help=f"Values between 0 and 1. How thick the stroke should be compared to font size. Currently: {profile.rStrokeWidth}.")
    wmGroup.add_argument("-H", "--height", type=float, help=f"Values between 0 and 1. How high the text should be relative to the image. Currently: {profile.rHeight}.")
    wmGroup.add_argument("-O", "--opacity", type=int, help=f"Values between 0 and 255. The opacity of the watermark. 0 is opaque, 255 is transparent. Currently: {profile.opacity}.")

    # Config management
    
    # Profile management

    pmGroup = parser.add_argument_group('Profile Management', 'All options allowing management of a profile')
    pmGroup.add_argument("-l", "--list-profiles", dest='list', action='store_true', help="List the names of all available profiles")
    pmGroup.add_argument("-w", "--show", nargs='+', help="Display the options saved in the provided profile")
    pmGroup.add_argument("--remove", nargs='+', help="Permanently delete the provided profile.")
    pmGroup.add_argument("-s", "--save", nargs='?', help="Save the provided profile. If none is given save to the current profile (as set by -p).", const='')
    return parser.parse_args()

def run():
    
    args, config = getArgsAndConfig()    
    if not configIsValid(config):
        return
    
    showProfile(args, config)
    listProfiles(args)
    doRemove(args)
    doSave(args, config)
    
    watermark(args.input, config)
                
def getArgsAndConfig() -> tuple:
    """Load default config, parse args, get config
    Raises:
        ValueError: If a bad profile was given

    Returns:
        tuple: args, config
    """
    config = ch.loadConfig()
    args = initArgParser(config)
    lm.getLogger().setLevel(args.logLevel.upper())            
    if args.profile and args.profile != config.activeProfile.name:
        newProfile = ch.loadProfile(args.profile)
        if newProfile:
            config.setActiveProfile(newProfile)
        else:
            raise ValueError(f"Profile '{args.profile}' not found")  

    config.merge(args)
    
    return args, config

def configIsValid(config:Config) -> bool:
    """Check config to make sure all needed information is there

    Args:
        config (WMConfig): The watermarker configuration object

    Returns:
        bool: True if there is no issue, False otherwise
    """
    profile = config.activeProfile
    if not profile.outDir:
        print("[[SEVERE]] No value for 'Output Folder' provided")
        logger.error("No value for 'Ouput Folder' provided")
        return False 
    
    if not profile.text:
        print("[[SEVERE]] No value for 'Text' provided!")
        logger.error("No value for 'Text' provided")
        return False
    
    if not os.path.exists(profile.outDir):
        print("[[WARNING]] Output Folder doesn't exist! Creating it at: " + str(profile.outDir))
        logger.warning(f"Output folder doesn't exist. Creating it at: {str(profile.outDir)}")
        os.mkdir(profile.outDir)
        
    return True

def showProfile(args: argparse.Namespace, config:Config) -> None:
    """Show details of the current profile if needed
    Args:
        args (argparse.Namespace): args obtained via argparse
        config (Config): Contains modified profile to save
    """
    if args.show:
        notFound = args.show
        profiles = ch.loadProfiles(args.show)
        print("\nProfiles:")
        for p in profiles:
            notFound.remove(p.name)
            print(
                f"""    {p.name}:
        Text:         {p.text}
        Font:         {p.font}
        Margin:       {p.margin}
        Stroke Width: {p.rStrokeWidth}
        Height:       {p.rHeight}
        Opacity:      {p.opacity}
        Destination:  {p.outDir}              
                """
            )
            
        if notFound:
            print("\nProfiles not found:")
            listNames(notFound)         

def listProfiles(args: argparse.Namespace) -> None:
    """List available profiles if needed
    Args:
        args (argparse.Namespace): args returned be argparse
    """
    if args.list:
        print('\nExisting profiles:')
        names = ch.listProfileNames()
        listNames(names)
        
def listNames(names:list):
    """Print names as a numbered list
    Args:
        names (list):
    """
    i = 0
    for name in names:
        i+=1
        print(f"    {i}. {name}")            
    print('')

def doRemove(args: argparse.Namespace) -> None:
    """Remove profiles if needed
    Args:
        args (argparse.Namespace): args obtained via argparse
    """
    if args.remove:
        print(f"Removing: '{args.remove}'")
        if not ch.removeProfiles(args.remove):
            print(f"Removing '{args.remove}' failed!")  
            
def doSave(args: argparse.Namespace, config:Config) -> None:
    """ Save a profile if needed
    Args:
        args (argparse.Namespace): args obtained via argparse
        config (Config): Contains modified profile to save
    """
    if args.save is not None:
        if args.save:
            print(f"Saving profil as '{args.save}'")
            config.activeProfile.setName(args.save)
        print('Saving Profile')
        if ch.saveProfile(config.activeProfile):
            print('Save successful!')
        else:
            print('Save failed!')             

def watermark(images:list, config:Config) -> None:
    """Watermark all provided images
    Args:
        images (list): A list of Paths of the images to watermark 
        config (Config): Configuration of the program
    """
    
    if not images:
        logger.debug('No images provided')
        return
    
    engine = WatermarkerEngine(config.activeProfile)
    
    print("Watermarking files:")
    logger.info("Watermarking files:")
    
    if os.name == 'nt':
        # Windows doesn't expand wildcards in shell, so we have to do it.
        globs = [ glob(str(p)) for p in images]
        images = [Path(p) for sub in globs for p in sub]
        logger.debug(f'Input after expanding globs: {images}')
    
    for path in images:
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
            
    
    print("Done!")
    logger.info("Done")
    
    
if __name__ == '__main__':
    main()