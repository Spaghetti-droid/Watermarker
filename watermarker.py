from PIL import UnidentifiedImageError
import os
import sys
import traceback
import logging
import argparse
from pathlib import Path
from glob import glob

import log.LogManager as lm
import config.ConfigHandler as ch
from config.Config import Config
from config.Profile import Profile
from engine.WatermarkerEngine import WatermarkerEngine
import config.validation as val

# Watermark all images in a folder
# TODO:
#   - Check image rotation loss is solved 

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
    parser.add_argument("input", type=Path, nargs='*', help="Paths to the images that we want to watermark.")
    
    # Global config
    
    cmGroup = parser.add_argument_group('Global Config', 'Options which affect the program globally')
    cmGroup.add_argument("-p", "--profile", help=f"Name of an existing profile to use as a default for watermark options. Default: '{config.defaultProfileName}'")
    cmGroup.add_argument("-P", "--default-profile", dest='defaultProfile', help='Change the default profile.')
    cmGroup.add_argument("--log-level", dest="logLevel", help=f"Level of detail for logged events. Default: '{config.logLevel}'")
    cmGroup.add_argument("--default-log-level", dest='defaultLogLevel', help='Change the default log level')

    # Profile

    wmGroup = parser.add_argument_group('Watermarking Profile', 'All options that can be saved in a profile. Most of these affect the appearance of the watermark in some way')

    wmGroup.add_argument("-d", "--destination-folder", dest='outDir', type=Path, help=f"Path to the folder containing where the watermarked pictures should go. Default: '{profile.outDir}'.")
    wmGroup.add_argument("-t", "--text", help=f"Text to use as watermark. Default: '{profile.text}'.")
    wmGroup.add_argument("-f", "--font",  help=f"Name or path of a font to be used in the watermark. If a name is used, the font must be installed on the system. Default: '{profile.font}'.")
    wmGroup.add_argument("-m", "--margin", type=float, help=f"Values between 0 and 1. The margin wanted between the watermark and the edge scaled for width and height. Default: {profile.margin}.")
    wmGroup.add_argument("-S", "--stroke-width", dest='strokeWidth', type=float, help=f"Values between 0 and 1. How thick the stroke should be compared to font size. Default: {profile.rStrokeWidth}.")
    wmGroup.add_argument("-H", "--height", type=float, help=f"Values between 0 and 1. How high the text should be relative to the image. Default: {profile.rHeight}.")
    wmGroup.add_argument("-O", "--opacity", type=int, help=f"Values between 0 and 255. The opacity of the watermark. 0 is opaque, 255 is transparent. Default: {profile.opacity}.")
    wmGroup.add_argument("-z", "--position", nargs=2, dest='xy', type=float, help=f"Relative position on the image of the anchor point. Default: {profile.xy}.")
    wmGroup.add_argument("-a", "--anchor-point", dest='anchor', help="Point on the watermark that is held at the position given by -z. This is a horizontal position followed by a vertical position." +
                         " Horizontal positions are: 'l' for left, 'm' for middle, 'r' for right." +
                         f" Vertical positions are: 't' for top, 'm' for middle, 'b' for bottom. Default: {profile.anchor}.")

    
    # Profile management

    pmGroup = parser.add_argument_group('Profile Management', 'All options allowing management of a profile')
    pmGroup.add_argument("-l", "--list-profiles", dest='list', action='store_true', help="List the names of all available profiles. The default profile is marked with a star.")
    pmGroup.add_argument("-w", "--show", nargs='*', help="Display the options saved in the provided profile")
    pmGroup.add_argument("--remove", nargs='+', help="Permanently delete the provided profile.")
    pmGroup.add_argument("-s", "--save", nargs='?', help="Save the provided profile. If none is given save to the current profile (as set by -p or -P).", const='')
    return parser.parse_args()

def run():
    
    args, config = getArgsAndConfig()    
    if not configIsValid(config):
        return
    
    saveDefaultLogLevel(args)
    saveDefaultProfile(args)
    showProfiles(args, config)
    listProfiles(args, config)
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
    
    # Handle log levels early
    
    if not args.logLevel and args.defaultLogLevel:
        args.logLevel = args.defaultLogLevel
        
    if args.logLevel:
        lm.getLogger().setLevel(args.logLevel.upper())  
    else:
        lm.getLogger().setLevel(config.logLevel)
        
    # Get profile to use as base for options
    
    if not args.profile and args.defaultProfile:
        args.profile = args.defaultProfile
                   
    if args.profile and args.profile != config.activeProfile.name:
        newProfile = ch.loadProfile(args.profile)
        if newProfile:
            config.setActiveProfile(newProfile)
        else:
            config.activeProfile.setLoadFailed()
            config.activeProfile.setName(args.profile)

    # Merge in user changes

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
    if profile.loadFailed:
        print(f"Profile '{profile.name}' was not found. The following profile values will be used:")
        displayProfile(profile)
        response = input("Proceed? (y/N)")
        if response.strip() != 'y':
            logger.warning("User cancelled")
            return False 
        else:
            logger.warning("User opted to proceed. Continuing.")
        
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
        
    error = val.checkMarginValue(profile) or val.checkXYValues(profile) or val.checkAnchorPoint(profile)
    if error:
        print(f"[[SEVERE]] {error}")  
        logger.error(error)  
        return False    
        
    return True

def saveDefaultProfile(args: argparse.Namespace) -> None:
    """Change which profile is used by default if needed
    Args:
        args (argparse.Namespace): args obtained via argparse
    """
    if args.defaultProfile:
        print(f"New default profile: {args.defaultProfile}")
        ch.updateDefaultProfile(args.defaultProfile)
        
def saveDefaultLogLevel(args: argparse.Namespace) -> None:
    """Change which log level is used by default if needed
    Args:
        args (argparse.Namespace): args obtained via argparse
    """
    if args.defaultLogLevel:
        print(f"New default log level: {args.defaultLogLevel.upper()}")
        ch.updateLogLevel(args.defaultLogLevel.upper())

def showProfiles(args: argparse.Namespace, config:Config) -> None:
    """Show details of the current profile if needed
    Args:
        args (argparse.Namespace): args obtained via argparse
        config (Config): Contains modified profile to save
    """
    if args.show == []:
        args.show = [ config.activeProfile.name ]
        print("\nCurrent Profile:")
    elif args.show:
        print("\nProfiles:")
    
    if args.show:
        notFound = args.show
        profiles = ch.loadProfiles(args.show)
        for p in profiles:
            notFound.remove(p.name)
            displayProfile(p)
            
        if notFound:
            print("\nProfiles not found:")
            listNames(notFound)       
            
def displayProfile(p:Profile):
    print(
        f"""    {p.name}:
        Text:         {p.text}
        Font:         {p.font}
        Stroke Width: {p.rStrokeWidth}        
        Opacity:      {p.opacity}
        Height:       {p.rHeight}
        Anchor:       {p.anchor}
        Position:     {p.xy}
        Margin:       {p.margin}
        Destination:  {p.outDir}              
        """
    )

def listProfiles(args: argparse.Namespace, config:Config) -> None:
    """List available profiles if needed
    Args:
        args (argparse.Namespace): args returned be argparse
    """
    if args.list:
        defaultName = config.defaultProfileName
        print('\nExisting profiles:')
        names = ch.listProfileNames()
        i = 0
        for name in names:
            i+=1
            print(f"{'*' if name == defaultName else ' '}   {i}. {name}")            
        print('')
        
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
            config.activeProfile.setName(args.save)
        print(f"Saving Profile '{config.activeProfile.name}'")
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
                engine.markAndSaveImage(path)
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