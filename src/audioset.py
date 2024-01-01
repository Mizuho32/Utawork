import os, sys, time
import csv, re
from enum import Flag, auto
import functools
import pathlib, datetime

import scipy
import numpy as np


class AudioSet:
    def __init__(self, label_path):
        self.labels, self.ids = self.load_label(label_path)

    def label_indices(self, result_output=None):
        return np.argsort(result_output, axis=1)[..., ::-1]

    def load_label(self, label_csv_path):
        with open(label_csv_path, 'r') as f:
            reader = csv.reader(f, delimiter=',')
            lines = list(reader)
        labels = []
        ids = []  # Each label has a unique id such as "/m/068hy"
        self.id_index = {} # id to index of infer result tensor
        for i1 in range(1, len(lines)):
            id = lines[i1][1]
            label = lines[i1][2]
            ids.append(id)
            labels.append(label)
            self.id_index[id] = i1-1
        return np.array(labels), np.array(ids)
