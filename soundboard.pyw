import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import askyesno, showerror
import os, random, sys, logging, re, wave, threading
from system_hotkey import SystemHotkey
from pyaudio import PyAudio, paInt16

# todo: add nicer colors to ui elements

# import pygame without that message
with open(os.devnull, 'w') as f:
    temp_stdout = sys.stdout
    sys.stdout = f
    import pygame
    from pygame import _sdl2
    pygame.init()
    sys.stdout = temp_stdout


def keybind_listener():
    hk = SystemHotkey()
    sfx = get_sfx()

    # sfx keybinds
    for i in range(0, len(sfx)):
        hk.register(['alt', bindable_chars[i]], callback=lambda event, s=sfx[i][0]: play(s))

    logging.debug(f'Using {len(sfx)} of {len(bindable_chars)} keybinds.')

    # control keybinds
    hk.register(['alt', '1'], callback=lambda event: stop())
    hk.register(['alt', '2'], callback=lambda event: pause())
    hk.register(['alt', '3'], callback=lambda event: unpause())
    hk.register(['alt', '4'], callback=lambda event: random_sound())


def get_sfx():
    if os.path.exists(sfx_dir):
        sfx_files = os.listdir(sfx_dir)
        sfx_filenames = [n.split('.')[0] for n in sfx_files]

        sfx_list = list(zip(sfx_files, sfx_filenames))

        if len(sfx_files) > len(bindable_chars):
            sfx_list = sfx_list[:len(bindable_chars)]
            logging.warning(f'One or more sfx have not been used due to a lack of keybind characters. '
                            f'The max amount of sfx is currently: {len(bindable_chars)}')

        return sfx_list
    else:
        os.mkdir(sfx_dir)
        sound_error_text.set('No sound effects! SFX folder has been created.')
        return []


class SoundGrid(tk.LabelFrame):
    def __init__(self, *args, **kwargs):
        tk.LabelFrame.__init__(self, *args, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        canvas.grid_propagate(False)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='nsew')

        data = get_sfx()

        if data:
            self.scrollable_frame.grid_columnconfigure(1, weight=1)

            tk.Label(self.scrollable_frame, text="Nr.", anchor="w").grid(row=0, column=0, sticky="ew")
            tk.Label(self.scrollable_frame, text="Sound Effects", anchor="w").grid(row=0, column=1, sticky="ew")
            tk.Label(self.scrollable_frame, text="Hotkeys", anchor="w").grid(row=0, column=2, sticky="ew")

            row = 0
            for file, name in data:

                tk.Label(self.scrollable_frame, text=str(row + 1), anchor="w").grid(row=row, column=0, sticky="ew", ipadx=5)
                tk.Button(self.scrollable_frame, text=name, command=lambda n=file: play(n)).grid(row=row, column=1, sticky="ew", ipadx=33)
                tk.Label(self.scrollable_frame, text=f'alt+{bindable_chars[row]}').grid(row=row, column=2, sticky="ew", ipadx=5)

                row += 1
        else:
            tk.Label(self.scrollable_frame, textvariable=sound_error_text, anchor="w").grid(row=0, column=0, sticky="ew")


class ControlGrid(tk.LabelFrame):
    def __init__(self, *args, **kwargs):
        tk.LabelFrame.__init__(self, *args, **kwargs)

        self.grid_columnconfigure(1, weight=1)

        y = -1

        def get_y_pos(x, skip=0):
            nonlocal y

            if skip:
                x = 0

            if not x:
                y += 1
                return y
            else:
                return y

        tk.Label(self, text='Stop sound').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        tk.Button(self, command=lambda: stop(), text="Stop (alt+1)", padx=10).grid(row=get_y_pos(1), column=1, sticky='ew')

        tk.Label(self, text='Pause sound').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        tk.Button(self, command=lambda: pause(), text="Pause (alt+2)", padx=10).grid(row=get_y_pos(1), column=1, sticky='ew')

        tk.Label(self, text='Resume sound').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        tk.Button(self, command=lambda: unpause(), text="Resume (alt+3)", padx=10).grid(row=get_y_pos(1), column=1, sticky='ew')

        tk.Label(self, text='Random sound').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        tk.Button(self, command=lambda: random_sound(), text="Random (alt+4)", padx=10).grid(row=get_y_pos(1), column=1, sticky='ew')

        tk.Label(self, text='Volume').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        volume_slider = tk.Scale(self, from_=0, to=100, orient=tk.HORIZONTAL, tickinterval=100, command=change_volume, variable=volume)
        volume_slider.set(50)
        volume_slider.grid(row=get_y_pos(1), column=1, sticky='ew')

        tk.Label(self, text='Playback Device').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        opts = ttk.Combobox(self, values=outputs, state='readonly')
        opts.bind('<<ComboboxSelected>>', change_device)
        opts.set('CABLE Input (VB-Audio Virtual Cable)' if 'CABLE Input (VB-Audio Virtual Cable)' in outputs else outputs[0])
        opts.grid(row=get_y_pos(1), column=1, sticky='ew')

        ttk.Checkbutton(self, text="Allow simultaneous playback", onvalue=1, offvalue=0, variable=simultaneous).grid(row=get_y_pos(1, True), column=1, sticky='w')
        ttk.Checkbutton(self, text="Loop", variable=loop, onvalue=1, offvalue=0).grid(row=get_y_pos(1, True), column=1, sticky='w')

        tk.Label(self, text='Recording').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        tk.Button(self, command=open_rec_menu, text="Open Recording Menu", padx=10).grid(row=get_y_pos(1), column=1, sticky='ew')

        tk.Label(self, text='Refresh').grid(row=get_y_pos(0), column=0, sticky=tk.E)
        tk.Button(self, command=refresh_sound_grid, text="Refresh Window", padx=10).grid(row=get_y_pos(1), column=1, sticky='ew')


class StoppableThread(threading.Thread):
    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class Recorder:
    def __init__(self, duration=10, verbose=False):
        self.frames = []
        self.duration = int(44100 / 1024 * duration)
        self.verbose = verbose
        self.t = StoppableThread(target=self.record)
        self.dev_index = 0
        self.p = PyAudio()
        self.usable = True

        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            if dev['name'] == 'Stereo Mix (Realtek(R) Audio)' and dev['hostApi'] == 0:
                self.dev_index = dev['index']
                break
        else:  # if not break
            logging.warning('Could not find stereo mix device. Is it disabled?')
            self.usable = False


    def start(self):
        self.t.start()
        if self.verbose: logging.debug(
            f'Starting recording.\n'
            f'Settings:\n\t'
            f'duration: {self.duration} (about {self.duration / 43} seconds)\n\t'
            f'verbose: {self.verbose}\n\t'
            f'frequency: 44100\n\t'
            f'channels: 2\n\t'
            f'chunk size: 1024\n\t'
            f'audio device index: {self.dev_index}')

    def stop(self):
        self.t.stop()
        logging.debug('Stopping recording.')

    def record(self):
        stream = self.p.open(
            format=paInt16,
            channels=2,
            rate=44100,
            frames_per_buffer=1024,
            input=True,
            input_device_index=self.dev_index
        )

        # 1 sec = 43.1 frames
        while not self.t.stopped():
            data = stream.read(1024)
            self.frames.append(data)

            if len(self.frames) > self.duration:
                self.frames = self.frames[43:]

    def is_recording(self):
        return self.t.is_alive()

    def save(self):
        if not self.t.is_alive(): return

        if not os.path.exists(rec_dir):
            os.makedirs(rec_dir)

        frames_to_save = self.frames.copy()
        filepath = os.path.join(rec_dir, f'{recording_file_name.get()}{self.get_latest_recording_no()}.wav')

        logging.debug(f'Creating wav file: {filepath}')
        wf = wave.open(filepath, 'wb')
        wf.setnchannels(2)
        wf.setsampwidth(self.p.get_sample_size(paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(frames_to_save))
        wf.close()
        logging.debug('File exported successfully.')

    @staticmethod
    def get_latest_recording_no():
        recs = os.listdir(rec_dir)

        if not recs: return 1
        numbers = []
        for rec in recs:
            match = re.match(rf'^.*(\d+)\.wav$', rec)
            if match:
                numbers.append(int(match.group(1)))

        return max(numbers) + 1


# todo: finish this
def open_rec_menu():
    if recorder.usable:
        recorder_window = tk.Toplevel(root)

        recorder_window.title("Recording Menu")
        recorder_window.geometry("300x200")

        tk.Label(recorder_window, textvariable=rec_text).pack()
        tk.Button(recorder_window, command=start_recording, text="Start Recording", padx=10).pack()
        tk.Button(recorder_window, command=stop_recording, text="Stop Recording", padx=10).pack()
        tk.Button(recorder_window, command=lambda: recorder.save(), text="Save Recording", padx=10).pack()

        tk.Label(recorder_window, text='').pack()
        tk.Label(recorder_window, text='File Name').pack()
        tk.Entry(recorder_window, textvariable=recording_file_name).pack()
    else:
        showerror('Recorder Unusable', 'Due to the Stereo Mix device being unavailable, the recorder cannot be used.')


def start_recording():
    recorder.start()
    rec_text.set('Recording')
    assert recorder.is_recording()


def stop_recording():
    recorder.stop()
    rec_text.set('Not Recording')


def play(sfx):
    if simultaneous.get():
        def play_nested():
            channel = pygame.mixer.find_channel()
            channel.set_volume(volume.get() / 100)
            channel.play(pygame.mixer.Sound('sfx/' + sfx), loops=(999 if loop.get() else 0))
        threading.Thread(target=play_nested).start()
    else:
        pygame.mixer.music.unload()
        pygame.mixer.music.load('sfx/' + sfx)
        pygame.mixer.music.play(loops=(999 if loop.get() else 0))


def stop():
    for i in range(0, (channel_amount + 1)):
        try:
            pygame.mixer.Channel(i).stop()
        except IndexError:
            continue

    pygame.mixer.music.stop()
    assert not pygame.mixer.get_busy()


def pause():
    for i in range(0, (channel_amount + 1)):
        try:
            pygame.mixer.Channel(i).pause()
        except IndexError:
            continue

    pygame.mixer.pause()
    assert pygame.mixer.get_busy()


def unpause():
    for i in range(0, (channel_amount + 1)):
        try:
            pygame.mixer.Channel(i).unpause()
        except IndexError:
            continue

    pygame.mixer.unpause()
    assert pygame.mixer.get_busy()


def random_sound():
    sfx = random.choice(get_sfx())
    play(sfx[0])


def change_volume(vol: str):
    for i in range(0, (channel_amount + 1)):
        try:
            pygame.mixer.Channel(i).set_volume(int(vol) / 100)
        except IndexError:
            continue

    pygame.mixer.music.set_volume(int(vol) / 100)


def change_device(event):
    logging.debug(f'Changing device to: {event.widget.get()}')
    pygame.mixer.quit()
    pygame.mixer.init(devicename=event.widget.get())
    pygame.mixer.music.set_volume(volume.get() / 100)


def save_callback(entry, window):
    recording_file_name.set(entry.get())
    window.destroy()


def on_closing():
    def destroy():
        pygame.mixer.quit()
        pygame.quit()
        root.destroy()

    if recorder.is_recording():
        if askyesno(title='Confirm Exit', message='You are still recording. Are you sure you want to quit?'):
            recorder.stop()
            while recorder.is_recording():
                continue
            destroy()
    else:
        destroy()


def get_envvars():
    if os.path.exists(os.path.join(os.getcwd(), '.env')):
        with open('.env') as stream:
            for line in stream:
                line = line.replace('\n', '')

                if not line or line.startswith('#'):
                    continue

                if line.lower().startswith('export '):
                    key, value = line.replace('export ', '', 1).strip().split('=', 1)
                else:
                    try:
                        key, value = line.strip().split('=', 1)
                    except ValueError:
                        logging.error(f"get_envvars error parsing line: '{line}'")
                        raise

                os.environ[key] = value
    else:
        with open('.env', 'w') as write:
            write.write('CHANNELS_AMT=256\nREC_VERBOSE=n\nDEBUG=n')
        get_envvars()


def init():
    global sound_grid

    logging.debug('Initializing...')

    # initialize modules pygame modules
    pygame.init()

    # set audio output device to vb cable if installed
    if 'CABLE Input (VB-Audio Virtual Cable)' in outputs:
        logging.debug('Using VB-Audio Virtual Cable')
        pygame.mixer.quit()
        pygame.mixer.init(devicename='CABLE Input (VB-Audio Virtual Cable)')
    else:
        logging.warning('VB Audio Virtual Cable was not found on your system.')
        pygame.mixer.init()

    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.set_num_channels(int(os.environ['CHANNELS_AMT']))

    logging.debug('Registering keybinds...')
    keybind_listener()
    logging.debug('Done!')

    root.title("Soundboard")
    root.geometry('600x320')
    root.resizable(width=False, height=False)

    root.columnconfigure(1, weight=1)

    ControlGrid(root, text="Controls").grid(row=0, column=0, sticky='nesw', padx=5, pady=10, ipadx=5, ipady=5)
    sound_grid.grid(row=0, column=1, sticky='nesw', padx=5, pady=10)

    root.protocol("WM_DELETE_WINDOW", on_closing)


def refresh_sound_grid():
    sound_grid.grid_forget()
    new_grid = SoundGrid(root, text=f'Sounds ({len(get_sfx())}/{len(bindable_chars)})')
    new_grid.grid(row=0, column=1, sticky='nesw', padx=5, pady=10)


if __name__ == "__main__":
    if os.name != 'nt':
        raise RuntimeError('This program does not (officially) support any platform other than Windows.')

    root = tk.Tk()

    # global variables
    volume = tk.IntVar(value=50)
    loop = tk.BooleanVar(value=False)
    simultaneous = tk.BooleanVar(value=True)
    rec_text = tk.StringVar(value='Not Recording')
    recording_file_name = tk.StringVar(value='recording')
    sound_error_text = tk.StringVar(value='No sound effects!')

    sfx_dir = os.path.join(os.getcwd(), 'sfx')
    rec_dir = os.path.join(os.getcwd(), 'recordings')

    outputs = pygame._sdl2.audio.get_audio_device_names(False)  # gets output devices
    bindable_chars = '567890qwertyuiopasdfghjklzxcvbnm'
    sound_grid = SoundGrid(root, text=f'Sounds ({len(get_sfx())}/{len(bindable_chars)})')

    get_envvars()

    logging.basicConfig(
        level=logging.DEBUG if os.environ['DEBUG'].startswith('y') else logging.INFO,
        format='[%(asctime)s][%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    channel_amount = int(os.environ['CHANNELS_AMT'])
    recorder_verbose = os.environ['REC_VERBOSE'].startswith('y')
    recorder = Recorder(duration=10, verbose=recorder_verbose)

    init()
    root.mainloop()
