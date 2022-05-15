import os, sys, csv, time
import importlib
import json, re

import ipywidgets as wdg
import librosa
import matplotlib.pyplot as plt
from ipywidgets import Layout, HBox, VBox
import numpy as np

def plot_all(metadata, idx, ontology, pygame, recog, show_txt=False):
    tmp={}
    txt = wdg.Textarea(value='', placeholder='', description='event:', disabled=False)

    def onclick(event):
        try:
            text = 'event.button=%d,  event.x=%d, event.y=%d, event.xdata=%f, event.ydata=%f' % (event.button, event.x, event.y, event.xdata, event.ydata)
            tmp["y_cut"] = tmp["wav"][..., int(tmp["sr"]*(event.xdata-tmp["start"])):-1]
            text += "\n" + str(tmp["y_cut"].shape)
            tr = list(reversed(range(len(tmp["wav"].shape))))
            sound = pygame.sndarray.make_sound((32768*tmp["y_cut"].transpose(*tr).copy(order="C")).astype(np.int16))
            sound.play()
            tmp["sound"] = sound
            txt.value = text
        except Exception as ex:
            txt.value = f"EX: {str(ex)}"

    button = wdg.Button(description='Stop')
    qbutton = wdg.Button(description="Quit")
    button.on_click(lambda b: tmp["sound"].stop())
    qbutton.on_click(lambda b: pygame.mixer.quit())

    cache = metadata["cache_list"][idx]
    tmp["sr"] = sr = cache["load_sr"]
    tmp["wav"] = wav = cache["wav"]
    tmp["start"] = start = cache["start"]
    data = cache["data"]

    # for stop, pygame.mixer.quit()
    pygame.mixer.pre_init(sr, size=-16, channels=len(wav.shape))
    pygame.mixer.init()

    fig, ax = plt.subplots(nrows=5, sharex=True)
    recog.Recog.waveplot(plt, librosa, wav, sr, ax=ax[0], offset=start, max_sr=2)
    recog.Recog.classifyshow(ontology, data["infer_series"], ax=ax[1])
    recog.Recog.state_show([recog.State.Music, recog.State.Talking, recog.State.Other], data["state_series"], ax=ax[2])
    recog.Recog.detect_show(data["detect_series"], ax=ax[3])
    recog.Recog.detect_show(data["detect_series_denoised"], xstep=int(cache["clip_len"]//35), ax=ax[4])

    fig.set_size_inches(16, 8)
    for a in ax:
        a.xaxis.grid()
    cid = fig.canvas.mpl_connect('button_press_event', onclick)

    ui = [button, qbutton]
    if show_txt:
        ui.append(txt)
    return HBox(ui)


def state_map(recog):
    all_states =[s for s in recog.State]
    mapping = {}

    for i, st1 in enumerate(all_states[:-1]):
        for st2 in all_states[i:]:
            st = st1|st2
            mapping[st.value] = st

    return mapping


def update_metadata(mapping, metadata):
    for cache in metadata["cache_list"]:
        d_series = cache["data"]["detect_series_denoised"]
        for time in d_series:
            d_series[time] = mapping[d_series[time].value]
