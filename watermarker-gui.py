import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
import threading as thr
from find_system_fonts_filename import get_system_fonts_filename, FindSystemFontsFilenameException
import logging
from PIL import ImageTk

import gui.utils
from gui.utils import Side
import log.LogManager as lm
import config.ConfigHandler as ch
import config.Profile as pr
import engine.WatermarkerEngine as we

# Logger and config initialisation

logging.basicConfig(format=lm.LOG_FORMAT, filename='Watermarker.log', level=lm.DEFAULT_LOG_LEVEL, filemode='w')
logger = lm.getLogger(__name__)
config = ch.loadConfig()
profile = config.activeProfile
lm.getLogger().setLevel(config.logLevel)

# Global events
class ProfileEvents:
    """Allows propagation of an event through all frames that are subscribed
    Listening frames must have the setVarsFromProfile() and updateProfile() methods
    """
    def __init__(self):
        self.listeners = []
    
    def addListener(self, listener) -> None:
        """ Add a listener that will be triggered by the methods below 
        Args:
            listener: Any object following the rules above
        """
        self.listeners.append(listener)
    
    def triggerSetVars(self) -> None:
        """ Triggers the setVarsFromProfile method in all listeners
        """
        for listener in self.listeners:
            listener.setVarsFromProfile()
            
    def triggerUpdate(self) -> bool:
        """Trigger the updateProfile method in all listeners
        Returns:
            bool: True if successful
        """
        try:
            for listener in self.listeners:
                listener.updateProfile()
            return True
        except Exception:
            logger.exception('Failed to update profiles')
            return False
            
profileEvents = ProfileEvents()

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
    ('All files', '*')
)

PREVIEW_BASE_LOCATION = Path("Assets/preview-base.jpg")

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
        
        self.profileFrame = ProfileFrame(self)
        self.profileFrame.pack(fill=tk.X, padx=5, pady=10)        
                
        ttk.Separator(self).pack(padx=5, fill=tk.X)
        
        inoutFrame = ttk.Frame(self)
        inoutFrame.pack(expand=True, fill=tk.BOTH)
        
        destFrame = DestFrame(inoutFrame)
        destFrame.pack(fill=tk.X, padx=5, pady=5)
        
        self.inputFrame = InputFrame(inoutFrame)
        self.inputFrame.pack(expand=True, fill=tk.BOTH, padx=5)
        
        textFrame = TextFrame(self)
        textFrame.pack(expand=True, fill=tk.X, padx=5, pady=5)
        
        appearanceFrame = AppearanceFrame(self)
        appearanceFrame.pack(expand=True, fill=tk.X, padx=5, pady=5)
        
        # Buttons

        buttonFrame = tk.Frame(self)
        buttonFrame.pack(fill=tk.X, pady=5)

        self.saveBtn = ttk.Button(buttonFrame, text='Save', command=self.saveConfig)
        self.saveBtn.pack(side=tk.LEFT, padx=10, pady=5, expand=True)
        
        self.previewBtn = ttk.Button(buttonFrame, text='Preview', command=self.showPreview)
        self.previewBtn.pack(side=tk.LEFT, padx=10, pady=5, expand=True)

        startBtn = ttk.Button(buttonFrame, text='Start', command=self.start)
        startBtn.pack(side=tk.LEFT, padx=10, pady=5, expand=True)
        ttk.Button(buttonFrame, text='Close', command=lambda:self.quit()).pack(side=tk.LEFT, padx=10, pady=5, expand=True)
        
    def start(self):
        """Create a new thread and start watermarking
        """
        self.updateConfig()
        if self.createOrCheckFolderPath():
            worker = WatermarkerThread(self.inputFrame.inputs, self)
            worker.start()
            
    def showPreview(self):
        """Generate a preview using current settings
        """
        self.updateConfig()
        if self.createOrCheckFolderPath():
            worker = PreviewThread(self)
            worker.start()
        
    def createOrCheckFolderPath(self) -> bool:
        """Create folder at config.outDir if it doesn't exist
        If it does exist, check that it is a folder
        Returns:
            bool: True if config.outDir points to a folder, which may have been created by this function 
        """        
        if not profile.outDir.exists():
            # umask can determine permissions
            profile.outDir.mkdir(0o777, True, True)
            return True
        elif not profile.outDir.is_dir():
            messagebox.showerror("Error", "Destination is not a folder!")
            logger.error(f"Destination is not a folder: {profile.outDir}")
            return False
        
        return True
          
    
    def saveConfig(self) -> None:
        """Save options as a file. Shows a message to the user if saving failed.
        """
        if not self.updateConfig():
            return
        if ch.saveProfile(profile):
            self.saveBtn.config(text='Saved!')
            self.saveBtn.after(500, self.resetSaveLabel)
            self.profileFrame.addToList(profile.name)
        else:
            messagebox.showerror("Error", "Failed to save!")
            
    def resetSaveLabel(self) -> None:
        self.saveBtn.config(text='Save')
        
    def updateConfig(self) -> bool:
        """Update config object with gui values
        Returns:
            bool: True if update succeeded, False otherwise
        """
        if profileEvents.triggerUpdate():
            return True            
        
        messagebox.showerror("Invalid parameters", "Please check your inputs and try again")
        return False
        
class ProfileFrame(ttk.Frame):
    """Contains profile management options
    """
    def __init__(self, master):
        super().__init__(master) 
        profileEvents.addListener(self) 
        
        # Init variables
        
        self.profileVar = tk.StringVar(value=profile.name) 
        self.profileNames = ch.listProfileNames()
        self.profileNames.sort()
        
        # Buttons and label
        
        lbFrame = ttk.Frame(self)
        selectedFilesLabel = ttk.Label(lbFrame, text='Current profile')
        selectedFilesLabel.pack(side=tk.LEFT)
        removeButton = ttk.Button(lbFrame, text='Delete', command=self.deleteProfile)
        removeButton.pack(side=tk.RIGHT)  
        self.makeDefaultButton = ttk.Button(lbFrame, text='Make Default', command=self.makeDefault)
        self.makeDefaultButton.config(state='disabled')
        self.makeDefaultButton.pack(side=tk.RIGHT)        
        lbFrame.pack(fill=tk.X, side=tk.TOP)
        
        # Combo box
        
        self.profileCombo = ttk.Combobox(self, textvariable=self.profileVar, values=self.profileNames)
        self.profileCombo.bind('<<ComboboxSelected>>', self.loadProfile)
        self.profileCombo.pack(fill=tk.X)
        
    def deleteProfile(self):
        """Delete the current profile
        """
        if messagebox.askokcancel("Delete profile", "Permanently delete this profile?"):
            toDelete = self.profileVar.get()
            ch.removeProfiles(toDelete)
            self.profileNames.remove(toDelete)
            self.profileCombo.config(values=self.profileNames)
            defaultDeleted = toDelete == config.defaultProfileName
            if not defaultDeleted:
                selected = config.defaultProfileName
            elif self.profileNames:
                selected = self.profileNames[0]
            else:
                selected = pr.DEFAULT_NAME
                
            self.profileVar.set(selected)
            self.loadProfile(selected)
            if defaultDeleted:
                self.makeDefault()                
    
    def makeDefault(self):
        """Make the current profile into the default one
        """
        ch.updateDefaultProfile(self.profileVar.get())
        config.defaultProfileName = self.profileVar.get()
        self.makeDefaultButton.config(state='disabled')
    
    def loadProfile(self, event):
        """Load profile from db and overwrite fields with its parameters
        Args:
            event:
        """
        global profile
        global config
        profile = ch.loadProfile(self.profileVar.get())
        config.setActiveProfile(profile)
        profileEvents.triggerSetVars()
        if profile.name == config.defaultProfileName:
            self.makeDefaultButton.config(state='disabled')
        else:
            self.makeDefaultButton.config(state='normal')
            
    def setVarsFromProfile(self) -> None:
        # Do nothing
        pass
    
    def updateProfile(self) -> None:
        # New name means new profile to save
        logger.debug("Updating profile name")
        profile.setName(self.profileVar.get())
        
    def addToList(self, newProfile:str) -> None:
        """Add a profile to the full list of profiles
        Args:
            newProfile (str): Name of the profile to add
        """
        if newProfile not in self.profileNames:
            self.profileNames.append(newProfile)
            self.profileNames.sort()
            self.profileCombo.config(values=self.profileNames)
            
class TextFrame(ttk.Frame):
    """ Frame that contains all options that visually impacts the watermark
    """
    def __init__(self, master):
        super().__init__(master) 
        profileEvents.addListener(self)
        
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
        
        self.fontVal = tk.StringVar(value=profile.font)
        self.textVal = tk.StringVar(value=profile.text)
        
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
            
    def selectFont(self):
        """Open a dialog, letting the user manually specify a font file
        """
        sel = fd.askopenfilename(title='Select a font', filetypes=FONT_TYPES)
        if sel:
            self.fontVal.set(sel)
            
    def updateProfile(self) -> None:
        logger.debug("Updating profile watermark settings")
        profile.setFont(self.fontVal.get())
        profile.setText(self.textVal.get())
        
    def setVarsFromProfile(self) -> None:
        logger.debug("Loading watermark settings")
        self.fontVal.set(profile.font)
        self.textVal.set(profile.text)
        
        
class AppearanceFrame(ttk.Frame):
    """ Frame that contains all options that visually impacts the watermark
    """
    
    X_ANCHORS = (("Left", "l"), ("", "m"), ("Right", "r"))
    Y_ANCHORS = (("Top", "t"), ("", "m"), ("Bottom", "b"))
    CANVAS_WIDTH = 400
    CANVAS_HEIGHT = 300
    POINT_RADIUS = 3
    # For reasons I don't understand, the canvas appears to have its origin (top left corner) at 2,2
    ORIGIN_OFFSET = 2    
    MARGIN_DRAW_SETTINGS = {'dash':(5,), 'fill':'deepskyblue4'}
    
    def __init__(self, master):
        super().__init__(master) 
        profileEvents.addListener(self)
        
        # Vars
        
        # Show percentages in gui, so multiply ratios by 100
        self.heightVal = tk.DoubleVar(value=profile.rHeight*100)
        self.strokeWidthVal = tk.DoubleVar(value=profile.rStrokeWidth*100)
        self.opacityVal = tk.IntVar(value=profile.opacity)
        self.marginVal = tk.DoubleVar(value=profile.margin*100)
        self.xVal = tk.DoubleVar(value=profile.xy[0]*100)
        self.yVal = tk.DoubleVar(value=profile.xy[1]*100)
        self.anchorVal = tk.StringVar(value=profile.anchor)
        
        # Traces
        
        self.anchorVal.trace_add('write', self._redrawMarginsAndWM)
        self.xVal.trace_add('write', self._redrawWM)
        self.yVal.trace_add('write', self._redrawWM)
        self.heightVal.trace_add('write', self._redrawWM)
        self.marginVal.trace_add('write', self._redrawMarginsAndWM)
        
        # Options
        
        sliderOptions = {'padx': 5, 'pady':5, 'expand': True, 'side':'left'}
        
        # Frames
        
        canvasFrame = self._makeCanvasFrame()
        canvasFrame.pack(pady=5, padx=5, side=tk.LEFT)
        
        appearanceFrame = ttk.Frame(self)
        opacityFrame = makeSliderFrame(appearanceFrame, 'Opacity', 0, 255, self.opacityVal, lambda v: self.opacityVal.set("{:.0f}".format(float(v))))
        opacityFrame.pack(**sliderOptions)  
        heightFrame = makeSliderFrame(appearanceFrame, 'Height (%)', 0, 100, self.heightVal, floatTruncator(self.heightVal))
        heightFrame.pack(**sliderOptions)
        strokeWidthFrame = makeSliderFrame(appearanceFrame, 'Stroke Width (%)', 0, 100, self.strokeWidthVal, floatTruncator(self.strokeWidthVal))
        strokeWidthFrame.pack(**sliderOptions)
        appearanceFrame.pack()
        
        anchorFrame = self._makeAnchorFrame()
        anchorFrame.pack(pady=5)
        
        posFrame = ttk.Frame(self)
        xFrame = makeSliderFrame(posFrame, 'X (%)', 0, 100, self.xVal, floatTruncator(self.xVal))
        xFrame.pack(**sliderOptions)
        yFrame = makeSliderFrame(posFrame, 'Y (%)', 0, 100, self.yVal, floatTruncator(self.yVal))
        yFrame.pack(**sliderOptions)
        marginFrame = makeSliderFrame(posFrame, 'Margin (%)', 0, 100, self.marginVal, floatTruncator(self.marginVal))
        marginFrame.pack(**sliderOptions)
        posFrame.pack()
    
    def _makeCanvasFrame(self) -> ttk.Frame:
        """Create the initial canvas

        Returns:
            ttk.Frame: canvas frame
        """        
        # Init optional objects for convenience
        
        self.marginLeft = None
        self.marginRight = None
        self.marginTop = None
        self.marginBottom = None
        
        # Create canvas frame
        
        canvasFrame = ttk.Frame(self)
        self.canvas = tk.Canvas(canvasFrame, bg='white', width=self.CANVAS_WIDTH, height=self.CANVAS_HEIGHT)
        self._drawMargins()
        self._drawRectangle()
        self.canvas.pack(anchor=tk.CENTER, expand=True)
        return canvasFrame
    
    def _drawRectangle(self) -> None:
        """Draw the watermark rectangle, and the anchor point
        """
        x = self.xVal.get()/100
        y = self.yVal.get()/100
        anchorX = x*self.CANVAS_WIDTH + self.ORIGIN_OFFSET
        anchorY = y*self.CANVAS_HEIGHT + self.ORIGIN_OFFSET
        margin = self.marginVal.get()/100
        anchor = self.anchorVal.get()
        # Real width of text here isn't particularly useful
        # So just scale width with text height
        width = self.CANVAS_WIDTH * gui.utils.getRatio(x, margin, anchor[0])
        maxHeight = self.CANVAS_HEIGHT * gui.utils.getRatio(y, margin, anchor[1])
        height = self.heightVal.get()/100*self.CANVAS_HEIGHT
        if height > maxHeight:
            height = maxHeight
        br, tl = gui.utils.getCorners(anchorX, anchorY, width, height, self.anchorVal.get())
        self.drawnWM = self.canvas.create_rectangle(*br, *tl, fill="grey", outline="")
        self.drawnAnchor = self._drawPoint(anchorX, anchorY)
        
    def _drawPoint(self, anchorX: float, anchorY: float) -> int:
        """Draw the anchor point
        Args:
            anchorX (float): x position of the point
            anchorY (float): y position of the point

        Returns:
            int: ID(?) of the point
        """
        logger.debug(f"Drawing anchor point at {anchorX}x{anchorY}")
        return self.canvas.create_oval(anchorX-self.POINT_RADIUS, anchorY-self.POINT_RADIUS, anchorX+self.POINT_RADIUS, anchorY+self.POINT_RADIUS, fill="red")
        
    def _redrawWM(self, r, w, u):
        """Remove current rectangle and point and redraw them
        
        Args:
            r (_type_):
            w (_type_):
            u (_type_):
        """
        self.canvas.delete(self.drawnWM)
        self.canvas.delete(self.drawnAnchor)
        self._drawRectangle()
        
    def _drawMargins(self) -> None:
        """Draw lines to show the margins
        """
        
        if not self.marginVal.get():
            return
        
        # Draw margins
        
        fullWidth = self.ORIGIN_OFFSET + self.CANVAS_WIDTH
        fullHeight = self.ORIGIN_OFFSET + self.CANVAS_HEIGHT
        widthAnchor = self.anchorVal.get()[0]
        heightAnchor = self.anchorVal.get()[1]
    
        if gui.utils.needMargin(widthAnchor, Side.LEFT):
            marginL = self.ORIGIN_OFFSET + self.marginVal.get()/100*self.CANVAS_WIDTH
            self.marginLeft = self.canvas.create_line(marginL, self.ORIGIN_OFFSET, marginL, fullHeight, **self.MARGIN_DRAW_SETTINGS)
        if gui.utils.needMargin(heightAnchor, Side.TOP):
            marginT = self.ORIGIN_OFFSET + self.marginVal.get()/100*self.CANVAS_HEIGHT
            self.marginTop = self.canvas.create_line(self.ORIGIN_OFFSET, marginT, fullWidth, marginT, **self.MARGIN_DRAW_SETTINGS)
        if gui.utils.needMargin(widthAnchor, Side.RIGHT):
            marginR = self.ORIGIN_OFFSET + self.CANVAS_WIDTH - self.marginVal.get()/100*self.CANVAS_WIDTH - 1
            self.marginRight = self.canvas.create_line(marginR, self.ORIGIN_OFFSET, marginR, fullHeight, **self.MARGIN_DRAW_SETTINGS)
        if gui.utils.needMargin(heightAnchor, Side.BOTTOM):
            marginB = self.ORIGIN_OFFSET + self.CANVAS_HEIGHT - self.marginVal.get()/100*self.CANVAS_HEIGHT - 1
            self.marginBottom = self.canvas.create_line(self.ORIGIN_OFFSET, marginB, fullWidth, marginB, **self.MARGIN_DRAW_SETTINGS)
        
    def _redrawMarginsAndWM(self, r, w, u):
        """Remove and redraw all visual components affected by the margins (and also the anchor point because it's easier)

        Args:
            r:
            w:
            u:
        """
        self.canvas.delete(self.marginLeft)
        self.canvas.delete(self.marginRight)
        self.canvas.delete(self.marginTop)
        self.canvas.delete(self.marginBottom)
        self._drawMargins()
        self._redrawWM(r, w, u)
          
    def _makeAnchorFrame(self) -> ttk.LabelFrame:
        """ Create the frame containing the anchor point selection

        Returns:
            ttk.LabelFrame:
        """
        anchorFrame = ttk.LabelFrame(self, text='Anchor Point')
        gridFrame = ttk.Frame(anchorFrame)
        row = 0
        for y in self.Y_ANCHORS:
            col = 0
            for x in self.X_ANCHORS:
                radio = ttk.Radiobutton(gridFrame, text=self._labelAnchor(x[0], y[0]), value=x[1]+y[1], variable=self.anchorVal)
                radio.grid(column=col, row=row, padx=10, pady=10, sticky=tk.NW)
                col += 1
            row += 1
            
        gridFrame.pack(fill=tk.X, padx=5)
        
        return anchorFrame
    
    @staticmethod
    def _labelAnchor(xText: str, yText: str) -> str:
        if xText or yText:
            return f"{yText} {xText}"
        return "Middle"
            
    def updateProfile(self) -> None:
        logger.debug("Updating profile position settings")
        profile.setOpacity(self.opacityVal.get())
        profile.setRHeight(self.heightVal.get()/100)
        profile.setRStrokeWidth(self.strokeWidthVal.get()/100)
        profile.setMargin(self.marginVal.get()/100)
        profile.setXY((self.xVal.get()/100, self.yVal.get()/100))
        profile.setAnchor(self.anchorVal.get())
        
    def setVarsFromProfile(self) -> None:
        logger.debug("Loading position settings")
        self.opacityVal.set(profile.opacity)
        self.heightVal.set(profile.rHeight*100)
        self.strokeWidthVal.set(profile.rStrokeWidth*100)
        self.marginVal.set(profile.margin*100)
        self.xVal.set(profile.xy[0]*100)
        self.yVal.set(profile.xy[1]*100)
        self.anchorVal.set(profile.anchor)
        
class DestFrame(ttk.Frame):
    """Frame controlling destination choice
    """
    def __init__(self, master):
        super().__init__(master)
        profileEvents.addListener(self)
        
        self.destFolder = tk.StringVar(value=profile.outDir)
        
        self.labelButtonFrame = makeLabelButtonFrame(self, 'Destination Folder', 'Browse', self.selectFolder)
        self.labelButtonFrame.pack(fill=tk.X, side=tk.TOP)
        #ttk.Label(self, text='Destination Folder').pack(side=tk.LEFT)
        ttk.Entry(self, textvariable=self.destFolder).pack(side=tk.LEFT, fill=tk.X, expand=True)
        #ttk.Button(self, text='Browse', command=self.selectFolder).pack(side=tk.LEFT)
        
    def selectFolder(self) -> None:
        """Open the file selection dialog and allow the user to choose a new destination.
        If a new destination is chosen, it is set to destFolder
        """
        newDest = fd.askdirectory(initialdir=self.destFolder, title='Destination Folder')
        if newDest:
            self.destFolder.set(newDest)
            
    def updateProfile(self) -> None:
        logger.debug("Updating profile destination settings")
        profile.setOutDir(self.destFolder.get())
        
    def setVarsFromProfile(self) -> None:
        logger.debug("Loading destination settings")
        self.destFolder.set(profile.outDir)
        
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
        
        engine = we.WatermarkerEngine(profile)
        i = 1
        for input in self.inputs:
            if self.isCancelled:
                break
            try:
                self.updateLabel(i)
                i+=1
                engine.markAndSaveImage(Path(input))
            except Exception:
                logger.exception(f"Failed to mark image at {input}")
            self.progressBar.step()
        self.pbWindow.destroy()
        
    def cancel(self):
        """Cancel the operation at the next file
        """
        self.isCancelled = True
        
class PreviewThread(thr.Thread):
    """Generates and shows a preview
    """
    def __init__(self, app):
        super().__init__()
        self.app = app
        
    def run(self):
        
        marked, exif = we.WatermarkerEngine(profile).markImage(PREVIEW_BASE_LOCATION)
        
        previewWindow = tk.Toplevel(self.app)
        previewWindow.title("Watermarker Preview")
        
        previewWindow.python_image = ImageTk.PhotoImage(marked)

        ttk.Label(previewWindow, image=previewWindow.python_image).pack()       
        
if __name__ == "__main__":
    app = App()
    app.mainloop()