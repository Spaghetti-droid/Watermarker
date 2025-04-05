import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
import threading as thr
from find_system_fonts_filename import get_system_fonts_filename, FindSystemFontsFilenameException
import logging

import LogManager as lm
import ConfigHandler as ch
import WatermarkerEngine as we

# Logger and config initialisation

logging.basicConfig(format=lm.LOG_FORMAT, filename='Watermarker.log', level=lm.DEFAULT_LOG_LEVEL, filemode='w')
logger = lm.getLogger(__name__)
config = ch.loadConfig()
lm.getLogger().setLevel(config.logLevel)

# Constants

FILE_TYPES = (
    ('Image files', '*.png'),
    ('Image files', '*.jpg'),
    ('Image files', '*.jpeg'),
    ('Image files', '*.webp'),
    ('All files', '*')
)

FONT_TYPES = (
    ('Fonts', '*.ttf'),
    ('Fonts', '*.ttc'),
    ('Fonts', '*.otf'),
    ('Fonts', '*.woff'),
    ('All files', '*')
)

# Global functions

def makeLabelButtonFrame(container, labelText:str, buttonText:str, command) -> ttk.Frame:
    """ Make a frame consisting of a label and a button. Both packed at opposite ends of the same row
    Args:
        container (Frame or Tk): Parent for the new frame
        labelText (str): Label text
        buttonText (str): Button text
        command (Function): Command executed when the button is clicked
    Returns:
        ttk.Frame: new frame
    """
    frame = ttk.Frame(container)
    frame.selectedFilesLabel = ttk.Label(frame, text=labelText)
    frame.selectedFilesLabel.pack(side=tk.LEFT)
    frame.inputButton = ttk.Button(frame, text=buttonText, command=command)
    frame.inputButton.pack(side=tk.RIGHT)
    
    return frame

def makeSliderFrame(container, labelText: str, from_, to, variable, command) -> ttk.Frame:
    """ Make a frame containing a label, a slider, and an entry box
    Args:
        container (Frame or Tk): The parent of the new frame
        labelText (str): Label text
        from_ (number): Min value of slider
        to (number): Max value of slider
        variable (Var): Variable tracked by slider and entry
        command (Function): Command to be executed when slider moves
    Returns:
        ttk.Frame: New slider frame
    """
    frame = ttk.Frame(container)
    label = ttk.Label(frame, text=labelText)
    label.pack()
    slider = ttk.Scale(frame, from_=from_, to=to, value=variable.get(), command=command)
    slider.pack()
    entry = ttk.Entry(frame, textvariable=variable)
    entry.pack()
    
    variable.trace_add('write', lambda *args: updateSlider(slider, variable))
    
    return frame

def updateSlider(slider: ttk.Scale, variable) -> None:
    """ Updates value of slider so that it keeps tracking variable
    Args:
        slider (ttk.Scale):
        variable (_type_): Any String/Int/Double/etc Var type
    """
    try:
        slider.config(value=variable.get())
    except Exception:
        logger.info('Bad variable format, slider not updated')

def floatTruncator(variable:tk.DoubleVar):
    """Return a function that sets a formatted version of its input into variable
    Args:
        variable (tk.DoubleVar):
    Returns:
        Lambda: Formatting and setting function
    """
    return lambda v: variable.set("{:.2f}".format(float(v)))

# Classes

class App(tk.Tk):
    """Root level graphical element
    """
    def __init__(self):
        super().__init__()
        self.title('Watermarker')        
        
        # Frames
        
        inoutFrame = ttk.Frame(self)
        inoutFrame.pack(expand=True, fill=tk.BOTH)
        
        destFrame = DestFrame(inoutFrame)
        destFrame.pack(fill=tk.X, padx=5, pady=5)
        
        self.inputFrame = InputFrame(inoutFrame)
        self.inputFrame.pack(expand=True, fill=tk.BOTH, padx=5)
        
        watermarkFrame = WatermarkFrame(self)
        watermarkFrame.pack(expand=True, fill=tk.X, padx=5, pady=5)
        
        # Buttons

        buttonFrame = tk.Frame(self)
        buttonFrame.pack(fill=tk.X, pady=5)

        self.saveBtn = ttk.Button(buttonFrame, text='Save', command=self.saveConfig)
        self.saveBtn.pack(side=tk.LEFT, padx=10, pady=5, expand=True)

        startBtn = ttk.Button(buttonFrame, text='Start', command=self.start)
        startBtn.pack(side=tk.LEFT, padx=10, pady=5, expand=True)
        ttk.Button(buttonFrame, text='Close', command=lambda:self.quit()).pack(side=tk.LEFT, padx=10, pady=5, expand=True)
        
        # Register frames containing config info
        
        self.configFrames = (
            destFrame,
            watermarkFrame
        )
        
    def start(self):
        """Create a new thread and start watermarking
        """
        self.updateConfig()
        if self.createOrCheckFolderPath():
            worker = WatermarkerThread(self.inputFrame.inputs, self)
            worker.start()
        
    def createOrCheckFolderPath(self) -> bool:
        """Create folder at config.outDir if it doesn't exist
        If it does exist, check that it is a folder
        Returns:
            bool: True if config.outDir points to a folder, which may have been created by this function 
        """        
        if not config.outDir.exists():
            config.outDir.mkdir(666, True, True)
            return True
        elif not config.outDir.is_dir():
            messagebox.showerror("Error", "Destination is not a folder!")
            logger.error(f"Destination is not a folder: {config.outDir}")
            return False
        
        return True
          
    
    def saveConfig(self) -> None:
        """Save options as a file. Shows a message to the user if saving failed.
        """
        if not self.updateConfig():
            return
        if ch.saveConfig(config):
            self.saveBtn.config(text='Saved!')
            self.saveBtn.after(500, self.resetSaveLabel)
        else:
            messagebox.showerror("Error", "Failed to save!")
            
    def resetSaveLabel(self) -> None:
        self.saveBtn.config(text='Save')
        
    def updateConfig(self) -> bool:
        """Update config object with gui values
        Returns:
            bool: True if update succeeded, False otherwise
        """
        try:
            for f in self.configFrames:
                f.updateConfig()
            
            return True
        except Exception:
            logger.exception('Failed to update config')
            messagebox.showerror("Invalid parameters", "Please check your inputs and try again")
            return False
        
        
class WatermarkFrame(ttk.Frame):
    """ Frame that contains all options that visually impacts the watermark
    """
    def __init__(self, master):
        super().__init__(master) 
        
        # Load fonts
        
        fonts=[]       
        try:
            fonts_filename = get_system_fonts_filename()
            for f in fonts_filename:
                #fonts.append(Path(f).name.lower())
                fonts.append(f)
            fonts.sort()
        except FindSystemFontsFilenameException:
            # Deal with the exception
            logger.exception("Couldn't find fonts")
            
        # Variables
        
        self.fontVal = tk.StringVar(value=config.font)
        self.textVal = tk.StringVar(value=config.text)
        self.marginVal = tk.DoubleVar(value=config.margin)
        self.heightVal = tk.DoubleVar(value=config.rHeight)
        self.strokeWidthVal = tk.DoubleVar(value=config.rStrokeWidth)
        self.opacityVal = tk.IntVar(value=config.opacity)
        
        # Frames
        
        textFrame = ttk.Frame(self)
        textLabelFrame = ttk.Frame(textFrame)
        textLabelFrame.pack(fill=tk.X)
        textLabel = ttk.Label(textLabelFrame, text='Text')
        textLabel.pack(side=tk.LEFT)
        textEntry = ttk.Entry(textFrame, textvariable=self.textVal)
        textEntry.pack(fill=tk.X)
        textFrame.pack(fill=tk.X, pady=5)
        
        self.fontFrame = ttk.Frame(self)
        self.fontFrame.pack(expand=True, fill=tk.X)        
        buttonLabelFrame = makeLabelButtonFrame(self.fontFrame, 'Font', 'Browse', self.selectFont)
        buttonLabelFrame.pack(fill=tk.X, side=tk.TOP)
        fontCombo = ttk.Combobox(self.fontFrame, textvariable=self.fontVal, values=fonts)
        fontCombo.pack(expand=True, fill=tk.X)
        
        sliderOptions = {'padx': 5, 'pady':5, 'expand': True, 'side':'left'}
        
        opacityFrame = makeSliderFrame(self, 'Opacity', 0, 255, self.opacityVal, lambda v: self.opacityVal.set("{:.0f}".format(float(v))))
        opacityFrame.pack(**sliderOptions)        
        
        heightFrame = makeSliderFrame(self, 'Height', 0, 1, self.heightVal, floatTruncator(self.heightVal))
        heightFrame.pack(**sliderOptions)
        
        strokeWidthFrame = makeSliderFrame(self, 'Stroke Width', 0, 1, self.strokeWidthVal, floatTruncator(self.strokeWidthVal))
        strokeWidthFrame.pack(**sliderOptions)
        
        marginFrame = makeSliderFrame(self, 'Margin', 0, 1, self.marginVal, floatTruncator(self.marginVal))
        marginFrame.pack(**sliderOptions)
            
    def selectFont(self):
        """Open a dialog, letting the user manually specify a font file
        """
        sel = fd.askopenfilename(title='Select a font', filetypes=FONT_TYPES)
        if sel:
            self.fontVal.set(sel)
            
    def updateConfig(self) -> None:
        config.setFont(self.fontVal.get())
        config.setMargin(self.marginVal.get())
        config.setOpacity(self.opacityVal.get())
        config.setRHeight(self.heightVal.get())
        config.setRStrokeWidth(self.strokeWidthVal.get())
        config.setText(self.textVal.get())

class DestFrame(ttk.Frame):
    """Frame controlling destination choice
    """
    def __init__(self, master):
        super().__init__(master)
        self.destFolder = tk.StringVar(value=config.outDir)
        
        self.labelButtonFrame = makeLabelButtonFrame(self, 'Destination Folder', 'Browse', self.selectFolder)
        self.labelButtonFrame.pack(fill=tk.X, side=tk.TOP)
        #ttk.Label(self, text='Destination Folder').pack(side=tk.LEFT)
        ttk.Entry(self, textvariable=self.destFolder).pack(side=tk.LEFT, fill=tk.X, expand=True)
        #ttk.Button(self, text='Browse', command=self.selectFolder).pack(side=tk.LEFT)
        
    def selectFolder(self) -> str:
        """Open the file selection dialog and allow the user to choose a new destination.
        If a new destination is chosen, it is set to destFolder
        """
        newDest = fd.askdirectory(initialdir=self.destFolder, title='Destination Folder')
        if newDest:
            self.destFolder.set(newDest)
            
    def updateConfig(self) -> None:
        config.setOutDir(self.destFolder.get())
        
class InputFrame(ttk.Frame):
    """ Frame containing elements that allow the user to choose images to process
    """
    
    def __init__(self, master):
        super().__init__(master)
        
        self.inputs = []
        
        self.labelButtonFrame = makeLabelButtonFrame(self, 'Selected Images', 'Choose', self.selectImages)
        self.labelButtonFrame.pack(fill=tk.X, side=tk.TOP)
        self.chosenFilesText = ScrolledText(self, height=3)
        self.chosenFilesText.bind("<Key>", lambda e: "break")
        self.chosenFilesText.pack(fill=tk.BOTH, expand=True)
    
    def selectImages(self):
        """Let user choose images and fill the chosenFilesText element with that choice
        """
        self.chosenFilesText.delete(1.0, tk.END)
        
        self.inputs = fd.askopenfilenames(title='Select images', filetypes=FILE_TYPES)
        numImages = len(self.inputs)
        for i in range(0, numImages):
            self.chosenFilesText.insert(f'{i+1}.0', self.inputs[i] + '\n')  
            
        self.labelButtonFrame.selectedFilesLabel.config(text=f'Selected Images ({numImages})')   
       
        
class WatermarkerThread(thr.Thread):
    """ A thread that takes charge of calling the engine to watermark the images
    """
    def __init__(self, inputs:list, app:App):
        """Initialise the thread
        Args:
            inputs (list): A list of images to watermark
            app (App): The main gui element
        """
        super().__init__()
        self.inputs = inputs
        self.app = app
    
    def updateLabel(self, next:int) -> None:
        self.pbLabel.config(text=f'Watermarking in progress ({next}/{self.numFiles})')
    
    def makeProgressBarWindow(self) -> None:
        """Generate a window containing the progress bar
        """
        self.numFiles = len(self.inputs)
        
        self.pbWindow = tk.Toplevel(self.app)
        self.pbWindow.title("Watermarking files")
        self.pbLabel = ttk.Label(self.pbWindow, text=f'Watermarking in progress (0/{self.numFiles})')
        self.pbLabel.pack()
        self.progressBar = ttk.Progressbar(self.pbWindow, length=200)
        self.progressBar.config(value=0, maximum=self.numFiles)
        self.progressBar.pack()
        self.isCancelled = False
        ttk.Button(self.pbWindow, text='Cancel', command=self.cancel).pack()
    
    def run(self):
        if not self.inputs:
            return
        
        self.makeProgressBarWindow()      
        
        # Watermark each file
        
        engine = we.WatermarkerEngine(config)
        i = 1
        for input in self.inputs:
            if self.isCancelled:
                break
            try:
                self.updateLabel(i)
                i+=1
                engine.markImage(Path(input))
            except Exception:
                logger.exception(f"Failed to mark image at {input}")
            self.progressBar.step()
        self.pbWindow.destroy()
        
    def cancel(self):
        """Cancel the operation at the next file
        """
        self.isCancelled = True
        
if __name__ == "__main__":
    app = App()
    app.mainloop()