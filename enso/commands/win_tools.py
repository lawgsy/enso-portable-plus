"""
A simple OO wrapper around the win32 Python modules.

By: Scott O. Nelson (aka "SirGnip")

February 2007 - March 2008

References:
Using win32 Python module to automate window's tasks (basically, can send any
event to any control in windows)
http://www.brunningonline.net/simon/blog/archives/000652.html

The gmane.comp.python.windows mailing list history is a good reference:
http://thread.gmane.org/gmane.comp.python.windows/
This mailing list is also called python-win32
"""

import win32gui
import win32api
import win32con
# import win32process
import win32clipboard
# import time
# import string
import ctypes
# import re
# import os
import logging

# import ctypes
# from ctypes import *
from ctypes import c_wchar_p, c_int, c_long, c_ulong
from ctypes import WinDLL, GetLastError, WinError, create_unicode_buffer
from ctypes.wintypes import HWND  # , RECT, POINT


# from enso.commands import CommandManager,
from enso.commands import CommandObject
# from enso.commands.factories import ArbitraryPostfixFactory
# from enso import selection
# from enso.messages import displayMessage
# from enso.contrib.scriptotron import ensoapi
# from SendKeys import SendKeys as sendkeys


def _stdcall(dllname, restype, funcname, *argtypes):
    """
    A decorator for a generator.

    The decorator loads the specified dll, retrieves the function with the
    specified name, set its restype and argtypes, it then invokes the generator
    which must yield twice: the first time it should yield the argument tuple to
    be passed to the dll function (and the yield returns the result of the
    call).
    It should then yield the result to be returned from the function call.
    """
    def decorate(func):
        api = getattr(WinDLL(dllname), funcname)
        api.restype = restype
        api.argtypes = argtypes

        def decorated(*args, **kw):
            iterator = func(*args, **kw)
            nargs = iterator.next()
            if not isinstance(nargs, tuple):
                nargs = (nargs,)
            try:
                res = api(*nargs)
            except Exception, e:
                return iterator.throw(e)
            return iterator.send(res)
        return decorated
    return decorate


def nonzero(result):
    """
    Raise error if zero.

    If the result is zero, and GetLastError() returns a non-zero error code,
    raise a WindowsError
    """
    if result == 0 and GetLastError():
        raise WinError()
    return result


@_stdcall("user32", c_int, "GetWindowTextLengthW", HWND)
def GetWindowTextLength(hwnd):
    """Return window title length."""
    yield nonzero((yield hwnd,))


@_stdcall("user32", c_int, "GetWindowTextW", HWND, c_wchar_p, c_int)
def GetWindowText(hwnd):
    """Return window title."""
    len = GetWindowTextLength(hwnd)+1
    buf = create_unicode_buffer(len)
    nonzero((yield hwnd, buf, len))
    yield buf.value


# Standalone functions
def GetTextFromClipboard():
    """Return text from clipboard."""
    win32clipboard.OpenClipboard()
    text = win32clipboard.GetClipboardData()
    win32clipboard.CloseClipboard()
    return(text)


def SetTextOnClipboard(text):
    """Write text to clipboard."""
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text)
    win32clipboard.CloseClipboard()


def is_app_window(win):
    """Determine if the window is an application window."""
    if not win32gui.IsWindow(win):
        return False

    # Invisible or disabled windows are of no interest
    if not win32gui.IsWindowVisible(win) or not win32gui.IsWindowEnabled(win):
        return False

    exstyle = win32gui.GetWindowLong(win, win32con.GWL_EXSTYLE)

    # AppWindow flag should be good at this point
    if exstyle & win32con.WS_EX_APPWINDOW != win32con.WS_EX_APPWINDOW:
        style = win32gui.GetWindowLong(win, win32con.GWL_STYLE)
        # Child window is suspicious
        if style & win32con.WS_CHILD == win32con.WS_CHILD:
            return False
        parent = win32gui.GetParent(win)
        owner = win32gui.GetWindow(win, win32con.GW_OWNER)
        # Also window which has parent or owner is probably not an application
        # window
        if parent > 0 or owner > 0:
            return False
        # Tool windows we also avoid
        # TODO: Avoid tool windows? Make exceptions? Make configurable?
        if exstyle & win32con.WS_EX_TOOLWINDOW == win32con.WS_EX_TOOLWINDOW:
            return False
    # There are some specific windows we do not want to switch to
    win_class = win32gui.GetClassName(win)
    screensaver_check = "WindowsScreensaverClass" == win_class
    if screensaver_check or "tooltips_class32" == win_class:
        return False
    # Now we probably have application window
    return True


def is_maximized_window(win):
    """Check if window is maximized."""
    placement = win32gui.GetWindowPlacement(win)
    maximized = placement[1] == win32con.SW_MAXIMIZE  # NOQA


class cRect(object):
    """
    Patterened from the Rect class in Pygame.

    See http://www.pygame.org/docs/ref/rect.html

    >>> r = cRect(1, 3, 10, 20)
    >>> r.size
    (10, 20)
    >>> r.size = (22, 44)
    >>> r.size
    (22, 44)
    >>> r.center
    (12, 25)

    # make sure that cRect functions the same as pygame's rect
    >>> p = pygame.Rect(r.left, r.top, r.width, r.height)
    >>> r.left == p.left
    True
    >>> r.right == p.right
    True
    >>> r.top == p.top
    True
    >>> r.bottom == p.bottom
    True

    >>> r.right = 99
    >>> p.right = 99
    >>> r.bottom = 300
    >>> p.bottom = 300
    >>> r.left == p.left
    True
    >>> r.right == p.right
    True
    >>> r.top == p.top
    True
    >>> r.bottom == p.bottom
    True

    >>> r.center = (70, 90)
    >>> p.center = (70, 90)
    >>> r.left == p.left
    True
    >>> r.right == p.right
    True
    >>> r.top == p.top
    True
    >>> r.bottom == p.bottom
    True
    >>> r.center == p.center
    True

    >>> r.midright == p.midright
    True
    """

    def __init__(self, l, t, w, h):
        """Initialization method."""
        self.left = l
        self.top = t
        self.width = w
        self.height = h

    def __str__(self):
        """Printable representation."""
        temp_rect = (self.left, self.top, self.width, self.height)
        return '<cRect %d, %d, %d, %d>' % temp_rect

    def __getattr__(self, name):
        """Called if an attribute can not be found through normal methods."""
        if name == 'right':
            return self.left + self.width
        elif name == 'bottom':
            return self.top + self.height
        elif name == 'topleft':
            return(self.left, self.top)
        elif name == 'bottomleft':
            return(self.left, self.bottom)
        elif name == 'topright':
            return(self.right, self.top)
        elif name == 'bottomright':
            return(self.right, self.bottom)
        elif name == 'midtop':
            return(self.centerx, self.top)
        elif name == 'midleft':
            return(self.left, self.centery)
        elif name == 'midbottom':
            return(self.centerx, self.bottom)
        elif name == 'midright':
            return(self.right, self.centery)
        elif name == 'size':
            return(self.width, self.height)
        elif name == 'centerx':
            return self.left + (self.width / 2)
        elif name == 'centery':
            return self.top + (self.height / 2)
        elif name == 'center':
            return(self.centerx, self.centery)

    def __setattr__(self, name, value):
        """Called every time an attribute is attempted to be set.

        Be careful of recursion...
        """
        if name == 'right':
            self.left = value - self.width
        elif name == 'bottom':
            self.top = value - self.height
        elif name == 'topleft':
            self.left = value[0]
            self.top = value[1]
        elif name == 'bottomleft':
            self.left = value[0]
            self.bottom = value[1]
        elif name == 'topright':
            self.right = value[0]
            self.top = value[1]
        elif name == 'bottomright':
            self.right = value[0]
            self.bottom = value[1]
        elif name == 'midtop':
            self.centerx = value[0]
            self.top = value[1]
        elif name == 'midleft':
            self.left = value[0]
            self.centery = value[1]
        elif name == 'midbottom':
            self.centerx = value[0]
            self.bottom = value[1]
        elif name == 'midright':
            self.right = value[0]
            self.centery = value[1]
        elif name == 'size':
            (self.width, self.height) = value
        elif name == 'centerx':
            self.left = value - self.width / 2
        elif name == 'centery':
            self.top = value - self.height / 2
        elif name == 'center':
            self.centerx = value[0]
            self.centery = value[1]
        else:
            # Not doing any special handling, call normal setattr so all other..
            object.__setattr__(self, name, value)


class cWindow:
    """Window class."""

    # win32gui.ShowWindow(394906, True) # makes win visible/invisible.

    def __init__(self, hwnd):
        """Initialise window."""
        if not win32gui.IsWindow(hwnd):
            assert 'Invalid window handle ID: %d' % hwnd
        self._hwnd = hwnd

    def __repr__(self):
        """The "formal" string representation."""
        return('<cWindow(%d)>' % self._hwnd)

    def __str__(self):
        """The "informal" string representation."""
        return('cWindow(%d)-%s' % (self.GetHwnd(), self.GetTitle()))

    def __eq__(self, rhs):
        """Equality ('==') operator."""
        return self._hwnd == rhs.GetHwnd()

    def __ne__(self, rhs):
        """inequality ('!=') operator."""
        return not self.__eq__(rhs)

    def GetClassName(self):
        """Return class name."""
        return(win32gui.GetClassName(self._hwnd))

    def IsVisible(self):
        """Return window visibility."""
        return(bool(win32gui.IsWindowVisible(self._hwnd)))

    def IsIconic(self):
        """Determine if window is minimized."""
        return(bool(win32gui.IsIconic(self._hwnd)))

    def GetHwnd(self):
        """Return window handle."""
        return self._hwnd

    def SetFocus(self):
        """Set focus to window."""
        win32gui.SetFocus(self._hwnd)

    def UpdateWindow(self):
        """Update window."""
        win32gui.UpdateWindow(self._hwnd)

    def EnableWindow(self, state):
        """Enable window."""
        win32gui.EnableWindow(self._hwnd, state)

    def GetTitle(self):
        """Return window title."""
        return(GetWindowText(self._hwnd))

    def SetTitle(self, newTitle):
        """Set window title."""
        win32gui.SetWindowText(self._hwnd, newTitle)

    def BringToTop(self):
        """Give the window the focus.

        This does not restore the window if it is minimized.
        """
        win32gui.BringWindowToTop(self._hwnd)

    # I think this is no longer supported?
    #  def BringToFront(self):
    #      win32gui.BringWindowToFront(self._hwnd)

    def SetAsForegroundWindow(self):
        """Move window to foreground."""
        win32gui.SetForegroundWindow(self._hwnd)

    def Close(self):
        """Close window."""
        win32gui.SendMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)

    def Maximize(self):
        """Maximise window."""
        win32gui.ShowWindow(self._hwnd, win32con.SW_MAXIMIZE)

    def Minimize(self):
        """Minimise window."""
        win32gui.ShowWindow(self._hwnd, win32con.SW_MINIMIZE)

    def Restore(self):
        """Restore window."""
        win32gui.ShowWindow(self._hwnd, win32con.SW_SHOWNOACTIVATE)
        """
        win32gui.SetWindowPos(
            fore_win.GetHwnd(),
            win32con.HWND_TOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE |
            win32con.SWP_NOZORDER | win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        """

    def GetRect(self):
        """Return rectangle defining position and size of the window."""
        (left, top, right, bottom) = win32gui.GetWindowRect(self._hwnd)
        return(cRect(left, top, right-left, bottom-top))

    def SetRect(self, rect):
        """Move and resize window based on given rectangle."""
        win32gui.MoveWindow(self._hwnd,
                            rect.left, rect.top, rect.width, rect.height, True)

    def GetPosition(self):
        """Get window position."""
        rect = win32gui.GetWindowRect(self._hwnd)
        return(rect[0], rect[1])

    def GetWidthHeight(self):
        """Get window width and height."""
        rect = win32gui.GetWindowRect(self._hwnd)
        return(rect[2] - rect[0], rect[3] - rect[1])

    def SetPosition(self, pos):
        """Set window position.

        win32gui.SetWindowPos and win32gui.MoveWindow do similar things with
        different options.
        Check out MSDN for details
        """
        win32gui.MoveWindow(self._hwnd, pos[0], pos[1],
                            self.GetWidthHeight()[0],
                            self.GetWidthHeight()[1], True)

    def SetWidthHeight(self, widthHeight):
        """Set window width and height."""
        win32gui.MoveWindow(self._hwnd,
                            self.GetPosition()[0], self.GetPosition()[1],
                            widthHeight[0], widthHeight[1], True)


class cDesktop:
    """Desktop class."""

    def __init__(self):
        """Initialisation."""
        pass

    @staticmethod
    def EnumCallback_AllWindows(hwnd, results):
        """Enumerate callback on all windows."""
        # results.append((hwnd, GetWindowText(hwnd)))
        results.append(cWindow(hwnd))

    @staticmethod
    def EnumCallback_TopLevelWindows(hwnd, results):
        """Enumerate callback on top windows."""
        w = cWindow(hwnd)
        if w.IsVisible():
            results.append(w)

    def GetAllWindows(self):
        """Return all windows."""
        windows = []
        win32gui.EnumWindows(cDesktop.EnumCallback_AllWindows, windows)
        return(windows)

    def GetTopLevelWindows(self):
        """Display all of the windows visible on the task bar and about 5 extra.

        I can get more specific with something like this snippet...
        gwl_style = GWL_STYLE
        if IsWindowVisible(hwnd):
            val = GetWindowLong(hwnd, gwl_style)
            if val & WS_VISIBLE:
                if not val & WS_CHILD:
                    if not val & WS_EX_TOOLWINDOW:
                        if val & WS_EX_CONTROLPARENT:
                            val = GetWindowLong(hwnd, gwl_style)
                            txt = GetWindowText(hwnd)
                            resultList.append((hwnd, txt))

        Or, from the web: "You can also GetDesktopWindow() and from that
        get all the child windows which includes most of the running apps."
        """
        windows = []
        win32gui.EnumWindows(cDesktop.EnumCallback_TopLevelWindows, windows)
        return(windows)

    def GetActiveWindow(self):
        """Get active window.

        I seem to have problems with this when it is run in a dos window?
        """
        return(cWindow(win32gui.GetActiveWindow()))

    def GetForegroundWindow(self):
        """Get front most window."""
        return(cWindow(win32gui.GetForegroundWindow()))

    def GetDesktopWindow(self):
        """Get desktop window."""
        return(cWindow(win32gui.GetDesktopWindow()))

    def FindWindowByTitle(self, title):
        """Find window by title.

        Name should be a exact match.
        (glob and regex can be added as other methods?)

        This only returns the first window found with the given name.
        """
        windows = self.GetAllWindows()
        for w in windows:
            if w.GetTitle() == title:
                return(w)
        return(None)

    def GetWorkArea(self):
        """Get work area."""
        class RECT(ctypes.Structure):
            _fields_ = [
                ('left', c_ulong),
                ('top', c_ulong),
                ('right', c_ulong),
                ('bottom', c_ulong)
            ]
        r = RECT()
        ctypes.windll.user32.SystemParametersInfoA(win32con.SPI_GETWORKAREA,
                                                   0, ctypes.byref(r), 0)
        logging.debug(map(int, (r.left, r.top, r.right, r.bottom)))
        return cRect(int(r.left), int(r.top), int(r.right), int(r.bottom))

    def GetCursorPosition(self):
        """Get cursor position in screen coordinates."""
        return(win32gui.GetCursorPos())

    def SetCursorPosition(self, posTuple):
        """Set cursor position.

        Also, check out win32api.mouse_event for a way to simulate a mouse event
        """
        win32api.SetCursorPos(posTuple)


'''
Commands to manipulate and arrange windows on your desktop

By: Scott O. Nelson (aka "SirGnip")
'''


class WindowsTaskbar:
    """Windows taskbar class."""

    ABM_GETSTATE = 4
    ABM_SETSTATE = 10

    ABS_AUTOHIDE = 0x01
    ABS_ONTOP = 0x02

    class APPBARDATA(ctypes.Structure):
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", c_long),
                ("top", c_long),
                ("right", c_long),
                ("bottom", c_long)
            ]

        _fields_ = [
            ("cbSize", c_long),
            ("hwnd", c_long),
            ("uCallbackMessage", c_long),
            ("uEdge", c_long),
            ("rc", RECT),
            ("lParam", c_long)
        ]

    def __init__(self):
        """Initialisation."""
        self.SHAppBarMessage = ctypes.windll.shell32.SHAppBarMessage
        # SHAppBarMessage.restype = APPBARDATA
        self.is_autohide_flag = self.is_autohide()

    def is_autohide(self):
        """Whether the taskbar will hide itself."""
        ABD = self.APPBARDATA()
        ABD.cbSize = ctypes.sizeof(ABD)
        # print ABD.cbSize

        self.SHAppBarMessage(self.ABM_GETSTATE, ctypes.byref(ABD))
        return ABD.lParam & self.ABS_AUTOHIDE

    def set_autohide(self, autohide_on):
        """Set whether the taskbar will hide itself."""
        self.is_autohide_flag = self.is_autohide()

        ABD = self.APPBARDATA()
        ABD.cbSize = ctypes.sizeof(ABD)
        if autohide_on:
            ABD.lParam = self.ABS_AUTOHIDE | self.ABS_ONTOP
        else:
            ABD.lParam = self.ABS_ONTOP
        self.SHAppBarMessage(self.ABM_SETSTATE, ctypes.byref(ABD))

    def undo_set_autohide(self):
        """Undo setting whether the taskbar will hide itself."""
        self.set_autohide(self.is_autohide_flag)


# import win32Wrap


# Globals
# provide desktop object to all classes in this module
DESK = cDesktop()
TASKBAR = WindowsTaskbar()


class SetWindowTitle(CommandObject):
    """Set the title of the window."""

    def __init__(self, parameter=None):
        """Initialisation."""
        CommandObject.__init__(self)
        self.parameter = parameter

    def __call__(self, ensoapi, parameter=None):
        """What to do if this class is called directly."""
        if parameter:
            win = DESK.GetForegroundWindow()
            win.SetTitle(parameter)

cmd_win_title = SetWindowTitle()


def cmd_height_to_maximum(ensoapi):
    """Maximize window height."""
    win = DESK.GetForegroundWindow()
    work_area = DESK.GetWorkArea()
    win_x, _ = win.GetPosition()
    win_width, _ = win.GetWidthHeight()
    win.SetPosition((win_x, work_area.top))
    win.SetWidthHeight((win_width, work_area.height - work_area.top))


def cmd_width_to_maximum(ensoapi):
    """Maximize window width."""
    win = DESK.GetForegroundWindow()
    work_area = DESK.GetWorkArea()
    _, win_y = win.GetPosition()
    _, win_height = win.GetWidthHeight()
    win.SetPosition((work_area.left, win_y))
    win.SetWidthHeight((work_area.right - work_area.left, win_height))


fullscreen_windows = {}


def cmd_fullscreen(ensoapi):
    """Put window into full-screen mode."""
    win = DESK.GetForegroundWindow()
    logging.debug(win)
    style = win32gui.GetWindowLong(win.GetHwnd(), win32con.GWL_STYLE)
    logging.debug(style)
    if style & (win32con.WS_CAPTION | win32con.WS_SIZEBOX) == 0:
        TASKBAR.undo_set_autohide()

        # Revert the fullscreen
        style = style | win32con.WS_CAPTION | win32con.WS_SIZEBOX
        logging.debug(style)
        win32gui.SetWindowLong(win.GetHwnd(), win32con.GWL_STYLE, style)
        if fullscreen_windows.get(win.GetHwnd()):
            (original_left,
             original_top,
             original_right,
             original_bottom,
             maximized
             ) = fullscreen_windows[win.GetHwnd()]
            win32gui.SetWindowPos(
                win.GetHwnd(),
                win32con.HWND_NOTOPMOST,
                original_left,
                original_top,
                original_right - original_left,
                original_bottom - original_top,
                win32con.SWP_NOOWNERZORDER | win32con.SWP_NOSENDCHANGING)
            if maximized:
                win.SetAsForegroundWindow()
                win.Maximize()
                # time.sleep(0.4)
            else:
                win.Restore()
            """
            win32gui.SetWindowPos(
                win.GetHwnd(),
                win32con.HWND_TOP,
                original_left,
                original_top,
                original_right - original_left,
                original_bottom - original_top,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            """
            # win.SetAsForegroundWindow()
            del fullscreen_windows[win.GetHwnd()]
    else:
        TASKBAR.set_autohide(True)

        placement = win32gui.GetWindowPlacement(win.GetHwnd())
        maximized = placement[1] == win32con.SW_MAXIMIZE
        print "maximized: " + repr(maximized)

        (original_left,
         original_top,
         original_right,
         original_bottom
         ) = win32gui.GetWindowRect(win.GetHwnd())
        # Make fullscreen
        # ex_style = win32gui.GetWindowLong(win.GetHwnd(), win32con.GWL_EXSTYLE)
        # ex_style = ex_style | win32con.WS_EX_TOPMOST
        # win32gui.SetWindowLong(win.GetHwnd(), win32con.GWL_EXSTYLE, ex_style)

        style = style & ~(win32con.WS_CAPTION | win32con.WS_SIZEBOX)
        print style
        win32gui.SetWindowLong(win.GetHwnd(), win32con.GWL_STYLE, style)

        menu_height = win32api.GetSystemMetrics(win32con.SM_CYMENU)
        width = win32api.GetSystemMetrics(0)
        height = win32api.GetSystemMetrics(1)
        win32gui.SetWindowPos(
            win.GetHwnd(),
            win32con.HWND_TOP,  # TOPMOST
            0,  # x, y, width, height?
            -menu_height,
            width,
            height + menu_height - 1,
            win32con.SWP_SHOWWINDOW)

        # win.Maximize()
        # win.BringToTop()

        fullscreen_windows[win.GetHwnd()] = (
            original_left,
            original_top,
            original_right,
            original_bottom,
            maximized)

    win.UpdateWindow()


def cmd_maximize(ensoapi):
    """Maximize window."""
    win = DESK.GetForegroundWindow()
    win.Maximize()


def cmd_minimize(ensoapi):
    """Minimize window."""
    win = DESK.GetForegroundWindow()
    win.Minimize()


def cmd_restore(ensoapi):
    """Restore window if it is maximized."""
    win = DESK.GetForegroundWindow()
    win.Restore()


def cmd_unmaximize(ensoapi):
    """Unmaximize window if it is maximized."""
    cmd_restore(ensoapi)


def cmd_close(ensoapi):
    """Close the window currently in the foreground."""
    win = DESK.GetForegroundWindow()
    win.Close()


class MinimizeAllWindows(CommandObject):
    """Minimize all visible windows."""

    def __init__(self, parameter=None):
        """Initialisation."""
        CommandObject.__init__(self)
        self.parameter = parameter

    def __call__(self, ensoapi):
        """What to do if this class is called directly."""
        for win in DESK.GetTopLevelWindows():
            if win.IsIconic():
                continue
            if win.GetTitle() in ('', 'Program Manager'):
                continue
            win.Minimize()

cmd_minimize_all = MinimizeAllWindows()


class RestoreAllWindows(CommandObject):
    """Restore all windows."""

    def __init__(self, parameter=None):
        """Initialisation."""
        CommandObject.__init__(self)
        self.parameter = parameter

    def __call__(self, ensoapi):
        """What to do if this class is called directly."""
        fore_win = DESK.GetForegroundWindow()
        win32gui.SetWindowPos(
            fore_win.GetHwnd(),
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,  # x, y, width, height?
            win32con.SWP_SHOWWINDOW | win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        for win in DESK.GetTopLevelWindows():
            if win.GetTitle() in ('', 'Program Manager'):
                continue
            if is_app_window(win.GetHwnd()) and \
               not is_maximized_window(win.GetHwnd()):
                win.Restore()
        fore_win.SetAsForegroundWindow()
        win32gui.SetWindowPos(
            fore_win.GetHwnd(),
            win32con.HWND_NOTOPMOST,
            0, 0, 0, 0,  # x, y, width, height?
            win32con.SWP_SHOWWINDOW | win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

cmd_restore_all = RestoreAllWindows()


class SoloWindow(CommandObject):
    """Minimize all windows except the current one."""

    def __init__(self, parameter=None):
        """Initialisation."""
        CommandObject.__init__(self)
        self.parameter = parameter

    def __call__(self, ensoapi):
        """What to do if this class is called directly."""
        fore_win = DESK.GetForegroundWindow()
        for win in DESK.GetTopLevelWindows():
            if is_app_window(win.GetHwnd()) and win != fore_win:
                win.Minimize()

cmd_solo = SoloWindow()


class SnapWindow(CommandObject):
    """Snap the window to the specified edge or corner of the screen."""

    def __init__(self, parameter=None):
        """Initialisation."""
        CommandObject.__init__(self)
        self.parameter = parameter

    def __call__(self, ensoapi, parameter=None):
        """What to do if this class is called directly."""
        try:
            win = DESK.GetForegroundWindow()
            winrect = win.GetRect()

            deskrect = DESK.GetDesktopWindow().GetRect()
            deskrect.height -= 30  # hack to make space for the taskbar

            if not win.IsVisible():
                return

            if parameter == 'left':
                winrect.left = 0
            elif parameter == 'top':
                winrect.top = 0
            elif parameter == 'right':
                winrect.right = deskrect.right
            elif parameter == 'bottom':
                winrect.bottom = deskrect.bottom
            elif parameter == 'nw':
                winrect.topleft = deskrect.topleft
            elif parameter == 'ne':
                winrect.topright = deskrect.topright
            elif parameter == 'sw':
                winrect.bottomleft = deskrect.bottomleft
            elif parameter == 'se':
                winrect.bottomright = deskrect.bottomright
            elif parameter == 'center':
                winrect.center = deskrect.center
            else:
                self.displayMessage('Invalid snap direction given')
                return
            win.SetRect(winrect)
        except Exception, e:
            msg = 'Exception thrown in the %s class' % self.__class__.__name__
            print '%s\n%s' % (msg, str(e))
            self.displayMessage(str(e), msg)

cmd_snap = SnapWindow()
cmd_snap.valid_args = (
        'left',
        'right',
        'top',
        'bottom',
        'nw',
        'ne',
        'sw',
        'se',
        'center'
    )
