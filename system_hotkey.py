import os
import _thread as thread
import time
import collections
import struct
import threading
from queue import Queue
import queue
from functools import wraps


class SystemHotkeyError(Exception): pass


class SystemRegisterError(SystemHotkeyError): pass


class UnregisterError(SystemHotkeyError): pass


class InvalidKeyError(SystemHotkeyError): pass


def bind_global_key(event_type, key_string, cb):
    return bind_key(event_type, root, key_string, cb)


def bind_key(event_type, wid, key_string, cb):
    assert event_type in ('KeyPress', 'KeyRelease')

    mods, kc = parse_keystring(key_string)
    key = (wid, mods, kc)

    if not kc:
        print('Could not find a keycode for %s' % key_string, file=sys.stderr)
        return False

    if not __keygrabs[key] and not grab_key(wid, mods, kc):
        return False

    __keybinds[key].append(cb)
    __keygrabs[key] += 1

    if not event.is_connected(event_type, wid, __run_keybind_callbacks):
        event.connect(event_type, wid, __run_keybind_callbacks)

    return True


def parse_keystring(key_string):
    modifiers = 0
    keycode = None

    for part in key_string.split('-'):
        if hasattr(xproto.KeyButMask, part):
            modifiers |= getattr(xproto.KeyButMask, part)
        else:
            if len(part) == 1:
                part = part.lower()
            keycode = lookup_string(part)

    return modifiers, keycode


def lookup_string(kstr):
    if kstr in keysyms:
        return get_keycode(keysyms[kstr])
    elif len(kstr) > 1 and kstr.capitalize() in keysyms:
        return get_keycode(keysyms[kstr.capitalize()])

    return None


def lookup_keysym(keysym):
    return get_keysym_string(keysym)


def get_min_max_keycode():
    return conn.get_setup().min_keycode, conn.get_setup().max_keycode


def get_keyboard_mapping():
    mn, mx = get_min_max_keycode()

    return conn.core.GetKeyboardMapping(mn, mx - mn + 1)


def get_keyboard_mapping_unchecked():
    mn, mx = get_min_max_keycode()

    return conn.core.GetKeyboardMappingUnchecked(mn, mx - mn + 1)


def get_keysym(keycode, col=0, kbmap=None):
    if kbmap is None:
        kbmap = __kbmap

    mn, mx = get_min_max_keycode()
    per = kbmap.keysyms_per_keycode
    ind = (keycode - mn) * per + col

    return kbmap.keysyms[ind]


def get_keysym_string(keysym):
    return keysym_strings.get(keysym, [None])[0]


def get_keycode(keysym):
    mn, mx = get_min_max_keycode()
    cols = __kbmap.keysyms_per_keycode
    for i in range(mn, mx + 1):
        for j in range(0, cols):
            ks = get_keysym(i, col=j)
            if ks == keysym:
                return i

    return None


def get_mod_for_key(keycode):
    return __keysmods.get(keycode, 0)


def get_keys_to_mods():
    mm = xproto.ModMask
    modmasks = [mm.Shift, mm.Lock, mm.Control, mm._1, mm._2, mm._3, mm._4, mm._5]  # order matters

    mods = conn.core.GetModifierMapping().reply()

    res = {}
    keyspermod = mods.keycodes_per_modifier
    for mmi in range(0, len(modmasks)):
        row = mmi * keyspermod
        for kc in mods.keycodes[row:row + keyspermod]:
            res[kc] = modmasks[mmi]

    return res


def get_modifiers(state):
    ret = []

    if state & xproto.ModMask.Shift:
        ret.append('Shift')
    if state & xproto.ModMask.Lock:
        ret.append('Lock')
    if state & xproto.ModMask.Control:
        ret.append('Control')
    if state & xproto.ModMask._1:
        ret.append('Mod1')
    if state & xproto.ModMask._2:
        ret.append('Mod2')
    if state & xproto.ModMask._3:
        ret.append('Mod3')
    if state & xproto.ModMask._4:
        ret.append('Mod4')
    if state & xproto.ModMask._5:
        ret.append('Mod5')
    if state & xproto.KeyButMask.Button1:
        ret.append('Button1')
    if state & xproto.KeyButMask.Button2:
        ret.append('Button2')
    if state & xproto.KeyButMask.Button3:
        ret.append('Button3')
    if state & xproto.KeyButMask.Button4:
        ret.append('Button4')
    if state & xproto.KeyButMask.Button5:
        ret.append('Button5')

    return ret


def grab_keyboard(grab_win):
    return conn.core.GrabKeyboard(False, grab_win, xproto.Time.CurrentTime,
                                  GM.Async, GM.Async).reply()


def ungrab_keyboard():
    conn.core.UngrabKeyboardChecked(xproto.Time.CurrentTime).check()


def grab_key(wid, modifiers, key):
    try:
        for mod in TRIVIAL_MODS:
            conn.core.GrabKeyChecked(True, wid, modifiers | mod, key, GM.Async,
                                     GM.Async).check()

        return True
    except xproto.BadAccess:
        return False


def ungrab_key(wid, modifiers, key):
    try:
        for mod in TRIVIAL_MODS:
            conn.core.UngrabKeyChecked(key, wid, modifiers | mod).check()
        return True
    except xproto.BadAccess:
        return False


def update_keyboard_mapping(e):
    global __kbmap, __keysmods

    newmap = get_keyboard_mapping().reply()

    if e is None:
        __kbmap = newmap
        __keysmods = get_keys_to_mods()
        return

    if e.request == xproto.Mapping.Keyboard:
        changes = {}
        for kc in range(*get_min_max_keycode()):
            knew = get_keysym(kc, kbmap=newmap)
            oldkc = get_keycode(knew)
            if oldkc != kc:
                changes[oldkc] = kc

        __kbmap = newmap
        __regrab(changes)
    elif e.request == xproto.Mapping.Modifier:
        __keysmods = get_keys_to_mods()


def __run_keybind_callbacks(e):
    kc, mods = e.detail, e.state
    for mod in TRIVIAL_MODS:
        mods &= ~mod

    key = (e.event, mods, kc)
    for cb in __keybinds.get(key, []):
        try:
            cb(e)
        except TypeError:
            cb()


def __regrab(changes):
    for wid, mods, kc in __keybinds:
        if kc in changes:
            ungrab_key(wid, mods, kc)
            grab_key(wid, mods, changes[kc])

            old = (wid, mods, kc)
            new = (wid, mods, changes[kc])
            __keybinds[new] = __keybinds[old]
            del __keybinds[old]


if os.name == 'nt':
    import ctypes
    from ctypes import wintypes
    import win32con

    byref = ctypes.byref
    user32 = ctypes.windll.user32
    PM_REMOVE = 0x0001

    vk_codes = {
        'a': 0x41,
        'b': 0x42,
        'c': 0x43,
        'd': 0x44,
        'e': 0x45,
        'f': 0x46,
        'g': 0x47,
        'h': 0x48,
        'i': 0x49,
        'j': 0x4A,
        'k': 0x4B,
        'l': 0x4C,
        'm': 0x4D,
        'n': 0x4E,
        'o': 0x5F,
        'p': 0x50,
        'q': 0x51,
        'r': 0x52,
        's': 0x53,
        't': 0x54,
        'u': 0x55,
        'v': 0x56,
        'w': 0x57,
        'x': 0x58,
        'y': 0x59,
        'z': 0x5A,
        '0': 0x30,
        '1': 0x31,
        '2': 0x32,
        '3': 0x33,
        '4': 0x34,
        '5': 0x35,
        '6': 0x36,
        '7': 0x37,
        '8': 0x38,
        '9': 0x39,
        "up": win32con.VK_UP,
        "kp_up": win32con.VK_UP,
        "down": win32con.VK_DOWN,
        "kp_down": win32con.VK_DOWN,
        "left": win32con.VK_LEFT,
        "kp_left": win32con.VK_LEFT,
        "right": win32con.VK_RIGHT,
        "kp_right": win32con.VK_RIGHT,
        "prior": win32con.VK_PRIOR,
        "kp_prior": win32con.VK_PRIOR,
        "next": win32con.VK_NEXT,
        "kp_next": win32con.VK_NEXT,
        "home": win32con.VK_HOME,
        "kp_home": win32con.VK_HOME,
        "end": win32con.VK_END,
        "kp_end": win32con.VK_END,
        "insert": win32con.VK_INSERT,
        "return": win32con.VK_RETURN,
        "tab": win32con.VK_TAB,
        "space": win32con.VK_SPACE,
        "backspace": win32con.VK_BACK,
        "delete": win32con.VK_DELETE,
        "escape": win32con.VK_ESCAPE,
        "pause": win32con.VK_PAUSE,
        "kp_multiply": win32con.VK_MULTIPLY,
        "kp_add": win32con.VK_ADD,
        "kp_separator": win32con.VK_SEPARATOR,
        "kp_subtract": win32con.VK_SUBTRACT,
        "kp_decimal": win32con.VK_DECIMAL,
        "kp_divide": win32con.VK_DIVIDE,
        "kp_0": win32con.VK_NUMPAD0,
        "kp_1": win32con.VK_NUMPAD1,
        "kp_2": win32con.VK_NUMPAD2,
        "kp_3": win32con.VK_NUMPAD3,
        "kp_4": win32con.VK_NUMPAD4,
        "kp_5": win32con.VK_NUMPAD5,
        "kp_6": win32con.VK_NUMPAD6,
        "kp_7": win32con.VK_NUMPAD7,
        "kp_8": win32con.VK_NUMPAD8,
        "kp_9": win32con.VK_NUMPAD9,
        "f1": win32con.VK_F1,
        "f2": win32con.VK_F2,
        "f3": win32con.VK_F3,
        "f4": win32con.VK_F4,
        "f5": win32con.VK_F5,
        "f6": win32con.VK_F6,
        "f7": win32con.VK_F7,
        "f8": win32con.VK_F8,
        "f9": win32con.VK_F9,
        "f10": win32con.VK_F10,
        "f11": win32con.VK_F11,
        "f12": win32con.VK_F12
    }
    win_modders = {
        "shift": win32con.MOD_SHIFT,
        "control": win32con.MOD_CONTROL,
        "alt": win32con.MOD_ALT,
        "super": win32con.MOD_WIN
    }
    win_trivial_mods = (
        0,
    )
else:
    from collections import defaultdict
    import sys

    from xcffib import xproto

    from xpybutil import conn, root, event
    from xpybutil.keysymdef import keysyms, keysym_strings

    __kbmap = None
    __keysmods = None

    __keybinds = defaultdict(list)
    __keygrabs = defaultdict(int)  # Key grab key -> number of grabs

    EM = xproto.EventMask
    GM = xproto.GrabMode
    TRIVIAL_MODS = [
        0,
        xproto.ModMask.Lock,
        xproto.ModMask._2,
        xproto.ModMask.Lock | xproto.ModMask._2
    ]

    if conn is not None:
        update_keyboard_mapping(None)
        event.connect('MappingNotify', None, update_keyboard_mapping)

    try:
        import xcffib
        from xcffib import xproto

        xcb_modifiers = {
            'control': xproto.ModMask.Control,
            'shift': xproto.ModMask.Shift,
            'alt': xproto.ModMask._1,
            'super': xproto.ModMask._4
        }
        xcb_trivial_mods = (
            0,
            xproto.ModMask.Lock,
            xproto.ModMask._2,
            xproto.ModMask.Lock | xproto.ModMask._2)
    except ImportError:
        pass
    else:
        try:
            from Xlib import X
            from Xlib import XK
            from Xlib.display import Display

            special_X_keysyms = {
                ' ': "space",
                '\t': "tab",
                '\n': "return",
                '\r': "return",
                '\e': "escape",
                '!': "exclam",
                '#': "numbersign",
                '%': "percent",
                '$': "dollar",
                '&': "ampersand",
                '"': "quotedbl",
                '\'': "apostrophe",
                '(': "parenleft",
                ')': "parenright",
                '*': "asterisk",
                '=': "equal",
                '+': "plus",
                ',': "comma",
                '-': "minus",
                '.': "period",
                '/': "slash",
                ':': "colon",
                ';': "semicolon",
                '<': "less",
                '>': "greater",
                '?': "question",
                '@': "at",
                '[': "bracketleft",
                ']': "bracketright",
                '\\': "backslash",
                '^': "asciicircum",
                '_': "underscore",
                '`': "grave",
                '{': "braceleft",
                '|': "bar",
                '}': "braceright",
                '~': "asciitilde"
            }

            xlib_modifiers = {
                'control': X.ControlMask,
                'shift': X.ShiftMask,
                'alt': X.Mod1Mask,
                'super': X.Mod4Mask
            }

            xlib_trivial_mods = (
                0,
                X.LockMask,
                X.Mod2Mask,
                X.LockMask | X.Mod2Mask)
        except ImportError:
            pass


class Aliases:
    def __init__(self, *aliases):
        self.aliases = {}
        for values in aliases:
            assert isinstance(values, tuple)
            for val in values:
                self.aliases[val] = values

    def get(self, thing, nonecase=None):
        return self.aliases.get(thing, nonecase)


def unique_int(values):
    last = 0
    for _ in values:
        if last not in values:
            break
        else:
            last += 1
    return last


class ExceptionSerializer:
    def __init__(self):
        self.queue = queue.Queue()

    def catch_and_raise(self, func, timeout=0.5):
        self.wait_event(func, timeout)
        self._check_for_errors()

    def mark_done(self, function):
        self.init_wrap(function)

        @wraps(function)
        def decorator(*args, **kwargs):
            self.clear_event(function)
            try:
                results = function(*args, **kwargs)
            except Exception as err:
                self.queue.put(err)
            else:
                return results
            finally:
                self.set_event(function)

        return decorator

    def put(self, x):
        self.queue.put(x)

    def init_wrap(self, func):
        name = self._make_event_name(func)
        e = threading.Event()
        setattr(self, name, e)

    def _check_for_errors(self):
        try:
            error = self.queue.get(block=False)
        except queue.Empty:
            pass
        else:
            raise error

    @staticmethod
    def _make_event_name(func):
        return '_event_' + func.__name__

    def get_event(self, func):
        return getattr(self, self._make_event_name(func))

    def set_event(self, func):
        self.get_event(func).set()

    def clear_event(self, func):
        self.get_event(func).clear()

    def wait_event(self, func, *args):
        self.get_event(func).wait(*args)


class CallSerializer:
    def __init__(self):
        self.queue = Queue()
        thread.start_new_thread(self.call_functions, (),)
        self.bug_catcher = ExceptionSerializer()

    def call_functions(self):
        while 1:
            func, args, kwargs = self.queue.get(block=True)
            func(*args, **kwargs)

    def serialize_call(self, timeout=0.5):
        def state(function):
            @wraps(function)
            def decorator(*args, **kwargs):
                mark_func = self.bug_catcher.mark_done(function)
                self.queue.put((mark_func, args, kwargs))
                self.bug_catcher.catch_and_raise(function, timeout)
            return decorator
        return state


NUMPAD_ALIASES = Aliases(
    ('kp_1', 'kp_end',),
    ('kp_2', 'kp_down',),
    ('kp_3', 'kp_next', 'kp_page_down'),
    ('kp_4', 'kp_left',),
    ('kp_5', 'kp_begin',),
    ('kp_6', 'kp_right',),
    ('kp_7', 'kp_home',),
    ('kp_8', 'kp_up',),
    ('kp_9', 'kp_prior', 'kp_page_up'),
)

thread_safe = CallSerializer()


class MixIn:
    @thread_safe.serialize_call(0.5)
    def register(self, hotkey, *args, callback=None, overwrite=False):
        assert isinstance(hotkey, collections.abc.Iterable) and type(hotkey) not in (str, bytes)
        if self.consumer == 'callback' and not callback:
            raise TypeError('Function register requires callback argument in non consumer mode')

        hotkey = self.order_hotkey(hotkey)
        keycode, masks = self.parse_hotkeylist(hotkey)

        if tuple(hotkey) in self.keybinds:
            if overwrite:
                self.unregister(hotkey)
            else:
                msg = 'existing bind detected... unregister or set overwrite to True'
                raise SystemRegisterError(msg, *hotkey)

        if os.name == 'nt':
            def nt_register():
                uniq = unique_int(self.hk_ref.keys())
                self.hk_ref[uniq] = (keycode, masks)
                self._the_grab(keycode, masks, uniq)

            self.hk_action_queue.put(lambda: nt_register())
            time.sleep(self.check_queue_interval * 3)
        else:
            self._the_grab(keycode, masks)

        if callback:
            self.keybinds[tuple(hotkey)] = callback
        else:
            self.keybinds[tuple(hotkey)] = args

        if os.name == 'posix' and self.use_xlib:
            self.disp.flush()

    @staticmethod
    def order_hotkey(hotkey):
        if len(hotkey) > 2:
            new_hotkey = []
            for mod in hotkey[:-1]:
                if 'control' == mod:
                    new_hotkey.append(mod)
            for mod in hotkey[:-1]:
                if 'shift' == mod:
                    new_hotkey.append(mod)
            for mod in hotkey[:-1]:
                if 'alt' == mod:
                    new_hotkey.append(mod)
            for mod in hotkey[:-1]:
                if 'super' == mod:
                    new_hotkey.append(mod)
            new_hotkey.append(hotkey[-1])
            hotkey = new_hotkey
        return hotkey

    def parse_hotkeylist(self, full_hotkey):
        masks = []
        keycode = self._get_keycode(full_hotkey[-1])
        if keycode is None:
            key = full_hotkey[-1]
            if key[:3].lower() == 'kp_':
                keycode = self._get_keycode('KP_' + full_hotkey[-1][3:].capitalize())
            if keycode is None:
                msg = 'Unable to Register, Key not understood by systemhotkey'
                raise InvalidKeyError(msg)

        if len(full_hotkey) > 1:
            for item in full_hotkey[:-1]:
                try:
                    masks.append(self.modders[item])
                except KeyError:
                    raise SystemRegisterError('Modifier: %s not supported' % item) from None
            masks = self.or_modifiers_together(masks)
        else:
            masks = 0
        return keycode, masks

    @staticmethod
    def or_modifiers_together(modifiers):
        result = 0
        for part in modifiers:
            result |= part
        return result

    def get_callback(self, hotkey):
        try:
            yield self.keybinds[tuple(hotkey)]
        except KeyError:
            aliases = NUMPAD_ALIASES.get(hotkey[-1])
            if aliases:
                for key in aliases:
                    try:
                        new_hotkey = hotkey[:-1]
                        new_hotkey.append(key)
                        yield self.keybinds[tuple(new_hotkey)]
                        break
                    except (KeyError, TypeError):
                        pass

    def parse_event(self, e):
        hotkey = []
        if os.name == 'posix':
            try:
                hotkey += self.get_modifiersym(e.state)
            except AttributeError:
                return None

            hotkey.append(self._get_keysym(e.detail).lower())
        else:
            keycode, modifiers = self.hk_ref[e.wParam][0], self.hk_ref[e.wParam][1]
            hotkey += self.get_modifiersym(modifiers)
            hotkey.append(self._get_keysym(keycode).lower())

        if os.name == 'posix':
            if tuple(hotkey) not in self.keybinds:
                return

        return hotkey

    def get_modifiersym(self, state):
        ret = []
        if state & self.modders['control']:
            ret.append('control')
        if state & self.modders['shift']:
            ret.append('shift')
        if state & self.modders['alt']:
            ret.append('alt')
        if state & self.modders['super']:
            ret.append('super')
        return ret

    def _get_keysym(self, keycode):
        """ given a keycode returns a keysym """


class SystemHotkey(MixIn):
    hk_ref = {}
    keybinds = {}

    def __init__(self, consumer='callback', check_queue_interval=0.0001, use_xlib=False, _conn=None,
                 unite_kp=True):
        self.use_xlib = use_xlib
        self.consumer = consumer
        self.check_queue_interval = check_queue_interval
        self.unite_kp = unite_kp
        if os.name == 'posix' and not unite_kp:
            raise NotImplementedError

        def mark_event_type(e):
            if os.name == 'posix':
                if self.use_xlib:
                    if e.type == X.KeyPress:
                        e.event_type = 'keypress'
                    elif e.type == X.KeyRelease:
                        e.event_type = 'keyrelease'
                else:
                    if isinstance(e, xproto.KeyPressEvent):
                        e.event_type = 'keypress'
                    if isinstance(e, xproto.KeyReleaseEvent):
                        e.event_type = 'keyrelease'
            else:
                e.event_type = 'keypress'
            return e

        self.data_queue = queue.Queue()
        if os.name == 'nt':
            self.hk_action_queue = queue.Queue()
            self.modders = win_modders
            self.trivial_mods = win_trivial_mods
            self._the_grab = self._nt_the_grab
            self._get_keycode = self._nt_get_keycode
            self._get_keysym = self._nt_get_keysym

            thread.start_new_thread(self._nt_wait, (), )

        elif use_xlib:
            self.modders = xlib_modifiers
            self.trivial_mods = xlib_trivial_mods
            self._the_grab = self._xlib_the_grab
            self._get_keycode = self._xlib_get_keycode
            self._get_keysym = self._xlib_get_keysym
            if not _conn:
                self.disp = Display()
            else:
                self.disp = _conn
            self.xRoot = self.disp.screen().root
            self.xRoot.change_attributes(event_mask=X.KeyPressMask)

            thread.start_new_thread(self._xlib_wait, (), )

        else:
            self.modders = xcb_modifiers
            self.trivial_mods = xcb_trivial_mods
            self._the_grab = self._xcb_the_grab
            self._get_keycode = self._xcb_get_keycode
            self._get_keysym = self._xcb_get_keysym
            if not _conn:
                self.conn = xcffib.connect()
            else:
                self.conn = _conn
            self.root = self.conn.get_setup().roots[0].root

            thread.start_new_thread(self._xcb_wait, (), )

        if consumer == 'callback':

            def thread_me():
                while 1:
                    time.sleep(self.check_queue_interval)
                    try:
                        e = self.data_queue.get(block=False)
                    except queue.Empty:
                        pass
                    else:
                        e = mark_event_type(e)
                        hotkey = self.parse_event(e)
                        if not hotkey:
                            continue
                        for cb in self.get_callback(hotkey):
                            if e.event_type == 'keypress':
                                cb(e)

            thread.start_new_thread(thread_me, (), )

        elif callable(consumer):
            def thread_me():
                while 1:
                    time.sleep(self.check_queue_interval)
                    try:
                        e = self.data_queue.get(block=False)
                    except queue.Empty:
                        pass
                    else:
                        hotkey = self.parse_event(mark_event_type(e))
                        if not hotkey:
                            continue
                        if e.event_type == 'keypress':
                            args = [cb for cb in self.get_callback(hotkey)]
                            consumer(e, hotkey, args)

            thread.start_new_thread(thread_me, (), )
        else:
            print('You need to handle grabbing events yourself!')

    def _xlib_wait(self):
        while 1:
            e = self.xRoot.display.next_event()
            self.data_queue.put(e)

    def _xcb_wait(self):
        while 1:
            e = self.conn.wait_for_event()
            self.data_queue.put(e)

    def _nt_wait(self):
        msg = ctypes.wintypes.MSG()
        while 1:
            try:
                remove_or_add = self.hk_action_queue.get(block=False)
            except queue.Empty:
                pass
            else:
                remove_or_add()
            if user32.PeekMessageA(byref(msg), 0, 0, 0, PM_REMOVE):
                if msg.message == win32con.WM_HOTKEY:
                    self.data_queue.put(msg)
                else:
                    print('some other message')
            time.sleep(self.check_queue_interval)

    @staticmethod
    def _nt_get_keycode(key):
        return vk_codes.get(key)

    @staticmethod
    def _nt_get_keysym(keycode):
        for key, value in vk_codes.items():
            if value == keycode:
                return key

    def _nt_the_grab(self, keycode, masks, _id):
        keysym = self._get_keysym(keycode)
        aliases = NUMPAD_ALIASES.get(keysym)
        if aliases and self.unite_kp:
            for alias in aliases:
                if alias != keysym and self._get_keycode(alias):
                    self.unite_kp = False
                    self._the_grab(self._get_keycode(alias), masks)
                    self.unite_kp = True

        if not user32.RegisterHotKey(None, _id, masks, keycode):
            keysym = self._nt_get_keysym(keycode)
            msg = 'The bind could be in use elsewhere: ' + keysym
            raise SystemRegisterError(msg)

    def _xlib_get_keycode(self, key):
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            try:
                keysym = XK.string_to_keysym(special_X_keysyms[key])
            except KeyError:
                return None
        keycode = self.disp.keysym_to_keycode(keysym)
        return keycode

    def _xlib_get_keysym(self, keycode, i=0):
        keysym = self.disp.keycode_to_keysym(keycode, i)
        return keysym_strings.get(keysym, [None])[0]

    def _xlib_the_grab(self, keycode, masks):
        for triv_mod in self.trivial_mods:
            self.xRoot.grab_key(keycode, triv_mod | masks, 1, X.GrabModeAsync, X.GrabModeAsync)

    def _xcb_the_grab(self, keycode, masks):
        try:
            for triv_mod in self.trivial_mods:
                try:
                    self.conn.core.GrabKeyChecked(
                        True,
                        self.root, triv_mod | masks, keycode,
                        xproto.GrabMode.Async, xproto.GrabMode.Async).check()
                except struct.error as e:
                    msg = 'Unable to Register, Key not understood by system_hotkey'
                    raise InvalidKeyError(msg) from e
        except xproto.AccessError as e:
            keysym = self._xcb_get_keysym(keycode)
            msg = 'The bind could be in use elsewhere: ' + keysym
            raise SystemRegisterError(msg) from e

    @staticmethod
    def _xcb_get_keycode(key):
        return lookup_string(key)

    @staticmethod
    def _xcb_get_keysym(keycode, i=0):
        keysym = get_keysym(keycode, i)
        return keysym_strings.get(keysym, [None])[0]

# this entire module is a massive mess
