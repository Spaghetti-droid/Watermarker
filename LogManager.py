import logging

LOGGING_ROOT = 'watermarker'
LOGGING_PREFIX = LOGGING_ROOT + '.'
DEFAULT_LOG_LEVEL = "WARNING"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"    

def getLogger(name:str=None) -> logging.Logger:
    """ Return a logger in the hierarchy below LOGGING_ROOT. 
    This allows the app to selectively apply logging levels to its files, without affecting imports.
    Args:
        name (str, optional):   Name of the logger to be added to the hierarchy.  
                                If not specified the app's root logger is provided instead.
    Returns:
        logging.Logger: A logger with name '<LOGGING_ROOT>.<name>'
    """
    if name:
        return logging.getLogger(LOGGING_PREFIX + name) 
    else:
        return logging.getLogger(LOGGING_ROOT)