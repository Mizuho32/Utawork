from typing import List, Dict, Tuple

from matplotlib.axes import Axes
import matplotlib.cm as cm
import torch, numpy as np

from . import utils

def classify_show(abst_tensor: torch.Tensor, abst_ids: List[str], ontology: utils.Ontology, xstep=1, ax: Axes = None, title=""):
    ax.imshow(abst_tensor.cpu().transpose(1,0), cmap='viridis', interpolation='nearest', aspect="auto")
    ax.set_title(title)

    #ax.set_xlabel('Time')
    #start, end = ax.get_xlim()
    #ax.xaxis.set_ticks(np.arange(start, end, xstep))

    labels = list(sorted(map(lambda i: ontology.to_name(i)[:7], abst_ids)))
    ax.set_yticks(np.arange(0, len(labels))+0.5*0)
    ax.set_yticklabels(labels)

def state_show(start_time: float, duration: float, state_series: Dict[str, np.ndarray], xstep=1, ax: Axes=None, title=""):
    labels = list(state_series.keys())
    label2yval = {name: i for i, name in enumerate(reversed(sorted(labels)))}
    colors = np.linspace(0, 100, len(labels))

    for label, yval in label2yval.items():
        for itv in state_series[label]:
            if itv[1] > start_time+duration:
                continue

            itv = itv-start_time
            itv = (max(0, itv[0]), min(duration, itv[1]-itv[0]))
            ax.broken_barh([itv], (yval, 1), facecolors=cm.jet(colors[yval]/100))

            ax.text(itv[0], yval+0.4, "<", color="white")
            ax.text(sum(itv)-0.5, yval+0.4, ">", color="white")

    ax.set_title(title)

    ax.set_xlabel('Time')
    ax.set_xlim([0, duration])
    start, end = ax.get_xlim()
    ax.xaxis.set_ticks(np.arange(start, end, xstep))

    ax.set_yticks(np.arange(0, len(labels))+0.5)
    ax.set_yticklabels(list(reversed(sorted(map(lambda name: name, labels)))))
