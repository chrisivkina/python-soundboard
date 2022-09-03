# Copyright (c) 2015, tim
# All rights reserved.

import os
import _thread as thread
import queue
import time
import collections
import struct

try:
    from . import util
except SystemError:
    import util


class SystemHotkeyError(Exception): pass


class SystemRegisterError(SystemHotkeyError): pass


class UnregisterError(SystemHotkeyError): pass


class InvalidKeyError(SystemHotkeyError): pass


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
        "shift": win32con.MOD_SHIFT
        , "control": win32con.MOD_CONTROL
        , "alt": win32con.MOD_ALT
        , "super": win32con.MOD_WIN
    }
    win_trivial_mods = (
        0,
    )
else:
    try:
        from . import xpybutil_keybind as keybind
    except SystemError:
        import xpybutil_keybind as keybind

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

thread_safe = util.CallSerializer()


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
                uniq = util.unique_int(self.hk_ref.keys())
                self.hk_ref[uniq] = ((keycode, masks))
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

    def or_modifiers_together(self, modifiers):
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

    def parse_event(self, event):
        hotkey = []
        if os.name == 'posix':
            try:
                hotkey += self.get_modifiersym(event.state)
            except AttributeError:
                return None

            hotkey.append(self._get_keysym(event.detail).lower())
        else:
            keycode, modifiers = self.hk_ref[event.wParam][0], self.hk_ref[event.wParam][1]
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

    def __init__(self, consumer='callback', check_queue_interval=0.0001, use_xlib=False, conn=None,
                 unite_kp=True):
        self.use_xlib = use_xlib
        self.consumer = consumer
        self.check_queue_interval = check_queue_interval
        self.unite_kp = unite_kp
        if os.name == 'posix' and not unite_kp:
            raise NotImplementedError

        def mark_event_type(event):
            if os.name == 'posix':
                if self.use_xlib:
                    if event.type == X.KeyPress:
                        event.event_type = 'keypress'
                    elif event.type == X.KeyRelease:
                        event.event_type = 'keyrelease'
                else:
                    if isinstance(event, xproto.KeyPressEvent):
                        event.event_type = 'keypress'
                    if isinstance(event, xproto.KeyReleaseEvent):
                        event.event_type = 'keyrelease'
            else:
                event.event_type = 'keypress'
            return event

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
            if not conn:
                self.disp = Display()
            else:
                self.disp = conn
            self.xRoot = self.disp.screen().root
            self.xRoot.change_attributes(event_mask=X.KeyPressMask)

            thread.start_new_thread(self._xlib_wait, (), )

        else:
            self.modders = xcb_modifiers
            self.trivial_mods = xcb_trivial_mods
            self._the_grab = self._xcb_the_grab
            self._get_keycode = self._xcb_get_keycode
            self._get_keysym = self._xcb_get_keysym
            if not conn:
                self.conn = xcffib.connect()
            else:
                self.conn = conn
            self.root = self.conn.get_setup().roots[0].root

            thread.start_new_thread(self._xcb_wait, (), )

        if consumer == 'callback':

            def thread_me():
                while 1:
                    time.sleep(self.check_queue_interval)
                    try:
                        event = self.data_queue.get(block=False)
                    except queue.Empty:
                        pass
                    else:
                        event = mark_event_type(event)
                        hotkey = self.parse_event(event)
                        if not hotkey:
                            continue
                        for cb in self.get_callback(hotkey):
                            if event.event_type == 'keypress':
                                cb(event)

            thread.start_new_thread(thread_me, (), )

        elif callable(consumer):
            def thread_me():
                while 1:
                    time.sleep(self.check_queue_interval)
                    try:
                        event = self.data_queue.get(block=False)
                    except queue.Empty:
                        pass
                    else:
                        hotkey = self.parse_event(mark_event_type(event))
                        if not hotkey:
                            continue
                        if event.event_type == 'keypress':
                            args = [cb for cb in self.get_callback(hotkey)]
                            consumer(event, hotkey, args)

            thread.start_new_thread(thread_me, (), )
        else:
            print('You need to handle grabbing events yourself!')

    def _xlib_wait(self):
        while 1:
            event = self.xRoot.display.next_event()
            self.data_queue.put(event)

    def _xcb_wait(self):
        while 1:
            event = self.conn.wait_for_event()
            self.data_queue.put(event)

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
        return keybind.keysym_strings.get(keysym, [None])[0]

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
        return keybind.lookup_string(key)

    @staticmethod
    def _xcb_get_keysym(keycode, i=0):
        keysym = keybind.get_keysym(keycode, i)
        return keybind.keysym_strings.get(keysym, [None])[0]

# this entire module is a massive mess
