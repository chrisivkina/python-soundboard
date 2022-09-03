import tkinter as tk
from tkinter import ttk
import pygame
from pygame import _sdl2
import os
import threading
import random
# from system_hotkey import SystemHotkey

# Gets sfx files from <current directory>/sfx
sfx_dir = './sfx'

# TODO: Add keybind system
#   use SystemHotkey


def get_sfx():
    if os.path.exists(sfx_dir):
        sfx_files = os.listdir(sfx_dir)
        sfx_filenames = [f.split('.')[0] for f in sfx_files]
        return list(zip(sfx_files, sfx_filenames))
    else:
        os.mkdir(sfx_dir)
        raise RuntimeError(f'There is no sfx directory. One has been created at {os.path.join(os.getcwd(), "sfx")}')


class SoundGrid(tk.LabelFrame):
    def __init__(self, *args, **kwargs):
        tk.LabelFrame.__init__(self, *args, **kwargs)
        data = get_sfx()

        self.grid_columnconfigure(1, weight=1)
        tk.Label(self, text="Nr.", anchor="w").grid(row=0, column=0, sticky="ew")
        tk.Label(self, text="Sound Effects", anchor="w").grid(row=0, column=3, sticky="ew")

        row = 1
        for (file, name) in data:
            nr_label = tk.Label(self, text=str(row), anchor="w")

            action_button = tk.Button(self, text=name, command=lambda f=file: play(f))

            nr_label.grid(row=row, column=0, sticky="ew")
            action_button.grid(row=row, column=3, sticky="ew")

            row += 1


class ControlGrid(tk.LabelFrame):
    def __init__(self, *args, **kwargs):
        tk.LabelFrame.__init__(self, *args, **kwargs)

        self.grid_columnconfigure(1, weight=1)
        row_n = -1
        x = 0

        def get_row_n():
            nonlocal row_n
            nonlocal x

            if x == 0:
                x += 1
                row_n += 1
                return row_n
            else:
                x = 0
                return row_n

        def get_row_cb():
            nonlocal row_n

            row_n += 1
            return row_n

        tk.Label(self, text='Stop sound').grid(row=get_row_n(), column=0, sticky=tk.E)
        tk.Button(self, command=stop, text="Stop", padx=10).grid(row=get_row_n(), column=1, sticky='ew')

        tk.Label(self, text='Random sound').grid(row=get_row_n(), column=0, sticky=tk.E)
        tk.Button(self, command=random_sound, text="Random", padx=10).grid(row=get_row_n(), column=1, sticky='ew')

        tk.Label(self, text='Volume').grid(row=get_row_n(), column=0, sticky=tk.E)
        volume_slider = tk.Scale(self, from_=0, to=100, orient=tk.HORIZONTAL, tickinterval=100, command=change_volume)
        volume_slider.set(50)
        volume_slider.grid(row=get_row_n(), column=1, sticky='ew')

        choices = get_devices()
        tk.Label(self, text='Playback Device').grid(row=get_row_n(), column=0, sticky=tk.E)
        opts = ttk.Combobox(self, values=choices, state='readonly')
        opts.bind('<<ComboboxSelected>>', change_device)
        opts.set('CABLE Input (VB-Audio Virtual Cable)' if 'CABLE Input (VB-Audio Virtual Cable)' in choices else choices[0])
        opts.grid(row=get_row_n(), column=1, sticky='ew')

        cb_value = tk.IntVar()
        cb = ttk.Checkbutton(self, text="Allow simultaneous playback", onvalue=1, offvalue=0, command=lambda: async_callback(get_cb_value()), variable=cb_value)
        cb.grid(row=get_row_cb(), column=1, sticky='w')

        def get_cb_value(): return cb_value.get()


def play(sfx):
    if _async:
        def play_nested():
            channel = pygame.mixer.find_channel()
            channel.play(pygame.mixer.Sound('sfx/' + sfx))
        threading.Thread(target=play_nested).start()
    else:
        pygame.mixer.music.unload()
        pygame.mixer.music.load('sfx/' + sfx)
        pygame.mixer.music.play()


def stop():
    if _async:
        for i in range(0, channel_amount):
            pygame.mixer.Channel(i).stop()
    else:
        pygame.mixer.music.stop()


def random_sound():
    sfx = random.choice(get_sfx())
    play(sfx[0])


def change_volume(vol: str):
    pygame.mixer.music.set_volume(int(vol) / 100)


def change_device(event):
    print(f'Changing device to: {event.widget.get()}')
    pygame.mixer.quit()
    pygame.mixer.init(devicename=event.widget.get())


def get_devices():
    return pygame._sdl2.audio.get_audio_device_names(False)


def async_callback(v):
    global _async

    _async = v


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Soundboard")

    pygame.init()

    pygame.mixer.init()
    outputs = get_devices()

    _async = 0

    if 'CABLE Input (VB-Audio Virtual Cable)' in outputs:
        print('Using VB-Audio Virtual Cable')
        pygame.mixer.quit()
        pygame.mixer.init(devicename='CABLE Input (VB-Audio Virtual Cable)')
    else:
        print('VB Audio Virtual Cable was not found on your system.')

    pygame.mixer.music.set_volume(0.5)

    channel_amount = 256
    pygame.mixer.set_num_channels(channel_amount)

    # # tip
    # tk.Label(text='Make sure you have VB Audio Virtual Cable\ninstalled, and you have "listen to this device" on.').pack()

    # controls
    ControlGrid(root, text="Controls").pack(fill="both", expand=True, padx=10, pady=10)

    # sounds
    SoundGrid(root, text="Sounds").pack(fill="both", expand=True, padx=10, pady=10)

    # geometry
    tk.Label(root, text='', width=50).pack(fill="both")

    root.mainloop()
