import json
import re
import numpy as np

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
