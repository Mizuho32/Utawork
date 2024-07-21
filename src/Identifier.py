import pathlib, glob, re, json
import pickle, time
from typing import List, Dict, Tuple
import urllib.parse
from bs4 import BeautifulSoup
from bs4.element import Tag
import requests
import pickle

from py_linq import Enumerable as E
import google.generativeai as genai

from .detector import Config
from .transcriber import Transcription
from . import utils

#from matplotlib.axes import Axes


def google(word: str) -> Tag:
    user_agent = "(｀・ω・´)"  # not to load images(?)

    search_url = "https://www.google.co.jp/search?hl=jp&gl=JP&"
    query = urllib.parse.urlencode({'q': word})
    search_url += query

    headers = {'User-Agent': user_agent.encode()}
    response = requests.get(search_url, headers=headers)
    response.raise_for_status()

    html = response.text#content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find('div', {'id': 'main'})
#.prettify()

def get_items(tag: Tag) -> List[str]:
    child_divs = tag.find_all('div', recursive=False)

    result_divs = [child_div for child_div in child_divs if child_div.find('h3')]
    result_divs = [div.find("h3").find("div") for div in result_divs]
    result_divs = [div for div in result_divs if not div.find("span")]

    return [div.text for div in result_divs]

class Identifier:

    def __init__(self, transcriptions: List[Transcription], model: genai.GenerativeModel, config: Config, prompt: str=""):
        self.model = model
        self.config = config
        self.transcriptions = transcriptions

        self.output_dir = self.config.input_path.parent / "identified"
        self.prompt = """
Guess the artist and the song name and return in json format include "artist" and "title" as keys.

{}
""" if not prompt else prompt


    def prepare(self,):
        if not self.output_dir.exists():
            self.output_dir.mkdir()

    def do_cache(self, transcribes: List[Transcription]):
        with open(self.output_dir / f"{self.config.input_path.stem}.pkl", "wb") as h:
            pickle.dump(transcribes, h)

    def guess_song(self, transcription: Transcription):

        segment = transcription.segment
        if segment[1] - segment[0] < self.config.thres_set.transc_long_thres:
            return {}

        
        # search lyrics
        if not transcription.search_result:
            text = transcription.text
            total_len = len(text)
            idx = total_len // 2
            search_word = text[idx:(idx+self.config.thres_set.search_len)]

            tags = google(search_word)
            items = get_items(tags)
            transcription.search_word = search_word
            transcription.search_result = items
        else:
            items = transcription.search_result
        

        prompt = self.prompt.format(str.join("\n", items))

        # guess song from search result
        if not transcription.llm_result:
            response = self.model.generate_content(prompt)
            llm_result = response.parts[0].text
            transcription.llm_result = llm_result
        else:
            llm_result = transcription.llm_result
        

        try:
            json_data = json.loads(re.search(r"\A```(?:json)?(.*)```\Z", llm_result, re.MULTILINE | re.DOTALL)[1])
        except (json.JSONDecodeError, TypeError) as e:
            print(f"JSON decoding error: {e}")
            json_data = {}

        if json_data:
            transcription.artist = json_data["artist"]
            transcription.title = json_data["title"]
        else:
            transcription.artist = ""
            transcription.title = ""
        
        return transcription

    def main(self) -> List[Transcription]:
        self.prepare()

        for idx, transcription in enumerate(self.transcriptions):
            self.guess_song(transcription)

            print(f"Guessed {idx}: {transcription.title}/{transcription.artist}")
            time.sleep(5)


        self.do_cache(self.transcriptions)

        return self.transcriptions


    def get_cache(self) -> List[Transcription]:
        return utils.load_pickle(self.output_dir / f"{self.config.input_path.stem}.pkl")