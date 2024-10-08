import json
import re, sys
from itertools import groupby
import scipy.signal as sps
import time
import pathlib
from typing import List, Dict, Tuple

import numpy as np
import pickle
from logging import getLogger, Formatter, StreamHandler, FileHandler, DEBUG, INFO, Logger


def load_pickle(path: pathlib.Path):
    with open(path, "rb") as h:
        data = pickle.load(h)
    return data

def save_text(path: pathlib.Path, text: str):
    with open(path, "w") as h:
        h.write(text)

# https://qiita.com/FukuharaYohei/items/92795107032c8c0bfd19
def get_module_logger(module, log_dir, verbose=True, console_print=True):
    logger = getLogger(module)

    if not logger.hasHandlers():
        if console_print:
            logger = _set_handler(logger, StreamHandler(sys.stdout), verbose)
        logger = _set_handler(logger, FileHandler(log_dir / "log.txt"), verbose)
    logger.setLevel(DEBUG)
    logger.propagate = False

    return logger

def _set_handler(logger, handler, verbose):
    if verbose:
        handler.setLevel(DEBUG)
    else:
        handler.setLevel(INFO)

    handler.setFormatter(Formatter('%(funcName)s %(lineno)s [%(levelname)s]: %(message)s'))
    logger.addHandler(handler)
    return logger

def killLogger(logger):
    if not logger == None:
        del Logger.manager.loggerDict[logger.name]

def append_or_overwrite(ar, idx, obj):
    if len(ar) == idx:
        ar.append(obj)
    elif len(ar) > idx:
        ar[idx] = obj
    else:
        raise IndexError(f"{idx} is out of array[{len(ar)}]")

def judges2str(js): # FIXME: judges shoul be classed (implement __repl__
    lf = "\n"
    return f'>>{js2s(js, " ", lf)}'

def js2s(js, prefix="", split=", "):
    return split.join(list(map(lambda t_j: f"{prefix}{sec2time(t_j[0])}: {repr(t_j[1])}", js.items())))

def sec2time(sec, digit=1):
    if type(sec) in [int, float, np.float64]:
        power = 10**digit
        s, ms = divmod(sec*power, power)
        if s >= 3600:
            return f'%s.%0{digit}d' % (time.strftime('%H:%M:%S', time.gmtime(s)), ms)
        else:
            return f'%s.%0{digit}d' % (time.strftime('%M:%S', time.gmtime(s)), ms)

    elif type(sec) == list:
        return repr(list(map(lambda n: sec2time(n), sec)))
    elif type(sec) == tuple:
        return repr(tuple(map(lambda n: sec2time(n), sec)))

def time2sec(time):
    if type(time) in[int, float, np.float64]:
        return time

    idx_num_pair = enumerate(reversed(list(map(lambda n: int(n), time.split(":")))))
    return sum(map(lambda i_n: i_n[1]* 60**i_n[0], idx_num_pair))

def resample(wav, orig_sr, dest_sr):
    number_of_samples = int(round(wav.shape[-1] * float(dest_sr) / orig_sr))
    return sps.resample(wav, number_of_samples, axis=1)

def reg(expr, ignore=True):
    if ignore:
        return re.compile(expr, re.IGNORECASE)
    else:
        return re.compile(expr)

def dicnone(d,k,v=None):
    try:
        return d[k]
    except KeyError:
        return v

def slice_wav(self, wav, sr, start, end):
    slice_start = int(sr*(start))
    slice_end   = int(sr*(end))

    if slice_start < 0 and slice_end > wav.shape[-1]:
        raise IndexError(f"Invalid slice {slice_start}:{slice_end} for {wav.shape}")

    return wav[..., slice_start:slice_end]

def wav_len(wav):
    return wav[-1]

# https://note.nkmk.me/python-round-decimal-quantize/
def round(val, digit=0):
    p = 10 ** digit
    return (val * p * 2 + 1) // 2 / p

# (from: https://stackoverflow.com/a/5878474/2885946)
def each_cons(x, size):
    return [x[i:i+size] for i in range(len(x)-size+1)]

def flatten(ar):
    return sum(ar, [])

# interval_state = {(start, durat): [states...]}
def each_state(interval_state):

    starts = {t: list(itv) for t, itv in groupby(sorted(interval_state.keys(), key=lambda itv: itv[0]), key=lambda itv: itv[0])}
    end_times = map(lambda itv: sum(itv), interval_state.keys())
    times = list(sorted(set([*starts.keys(), *end_times])))

    for cur, nxt in each_cons(times, 2):

        covering_starts = list(filter(lambda t: t <= cur, starts.keys()))

        if covering_starts:
            cand = flatten(list(map(lambda t: starts[t], covering_starts)))
            covering_itvs = list(filter(lambda itv: nxt <= sum(itv), cand))

            cur_itv = (cur, nxt-cur)
            states = flatten(list(map(lambda itv: interval_state[itv], covering_itvs)))
            yield (cur_itv, states)


def if_not_defined(level, name, val):
    vars_ = vars(sys.modules[level])
    if not name in vars_ or not vars_[name]:
        return val
    else:
        return vars_[name]

def vars_get(context, setget):

    #if   type(setget) == dict:
    #    for k, v in setget.items():
    #        context[k] = v
    if hasattr(setget, "__iter__"):
        ck = context.keys()
        return {k: context[k] for k in setget if k in ck}


class Ontology:

    def __init__(self, jsonpath):
        self.json = json.load(open(jsonpath, 'r'))
        self.ontology = Ontology.load_onto(self.json)

    # id array -> readable names
    def to_name(self, ids):
        if type(ids) is list:
            return list(map(lambda id: self.ontology[id]["name"], ids))
        elif type(ids) is str:
            return self.ontology[ids]["name"]

    # access items by integer, string(id), regexp(name)
    def __getitem__(self, ident):
        if type(ident) is int:
            return self.json[ident]
        elif type(ident) in [str, np.str_]:
            if ident[0] == "/":
                return self.ontology[ident]
            else:
                return self[re.compile(ident)]
        elif type(ident) is re.Pattern:
            return [itm for itm in self.json if ident.search(itm["name"])]


    # concrete node -> abstract node
    def get_abst(self, ident, terminals):
        #print(ident, type(ident))
        if type(ident) in [str, np.str_]:
            ident = self.ontology[ident]

        ident_abstest = dicnone(ident,"parent_ids") or ident["id"]
        ancestors = [ter for ter in terminals if ident_abstest == dicnone(ter,  "parent_ids") or ter["id"] ]
        if len(ancestors) > 0:          # return most concrete abstract class
            for anc in ancestors:
                if anc["id"] in dicnone(ident, "parent_ids", []):
                    return self.ontology[anc["id"]]

        return self.ontology[dicnone(ident,"parent_ids", [ident["id"]])[-1]] # most abstract class


    # {concrete class: score} -> {abstract class: score}
    def abst_scores(self, ccls_score_map, absts):
        abst_score_map = {}

        for cls, score in ccls_score_map.items():
            #print(cls, score)
            abst_cls = self.get_abst(cls, absts)
            abst_id = abst_cls["id"]

            if not abst_id in abst_score_map.keys():
                abst_score_map[abst_id] = score
            else:
                abst_score_map[abst_id] += score

        return abst_score_map

    def absts_conc_indices(self, interests: List[dict], audioset) -> Dict[str, List[int]]:
        conc_ids = [audioset.ids[idx] for idx in range(527)]
        abst_concidx_map = {}

        for cls in conc_ids:
            #print(cls, score)
            abst_cls = self.get_abst(cls, interests)
            abst_id = abst_cls["id"]

            try:
                cls_index = audioset.id_index[cls] # index in infer out tensor

                if not abst_id in abst_concidx_map.keys():
                    abst_concidx_map[abst_id] = [cls_index]

                    abst_index = audioset.id_index[abst_id]
                    abst_concidx_map[abst_id].append(abst_index)
                else:
                    abst_concidx_map[abst_id].append(cls_index)
            except KeyError:
                pass

        return abst_concidx_map






    @classmethod
    def load_onto(cls, j):
        terms = {}
        nonterms = {}

        for n in j:
            if n["child_ids"]:
                nonterms[n["id"]] = n
            else:
                terms[n["id"]] = n

        for key, val in nonterms.items():
            for child_id in val["child_ids"]:
                try:
                    nonterms[child_id]["parent_id"] = key
                except KeyError as e:
                    terms[child_id]["parent_id"] = key

        total = {**terms, **nonterms}

        for ident, content in total.items():

            if "parent_id" in content.keys() and not "parent_ids" in content.keys():
                parents = [total[content["parent_id"]]]
                while "parent_id" in parents[-1].keys():
                    parents.append(total[parents[-1]["parent_id"]])
                content["parent_ids"] = list(map(lambda itm: itm["id"], parents))

                #print(range(len(parents)-1))
                for i in range(len(parents)-1):
                    #print(parents[i]["name"])
                    parents[i]["parent_ids"] = list(map(lambda itm: itm["id"], parents[i+1:]))

            #print(content["name"], to_name(content["parent_ids"]) )
            #for pid in content["parent_ids"]:
            #    pa = total[pid]
            #    #print(pa["name"])
            #    if "parent_ids" in pa.keys():
            #        print(to_name(pa["parent_ids"]))
            #break

        return total
