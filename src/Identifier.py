import csv
import pathlib, glob, re, json
import pickle, time
from typing import List, Dict, Tuple, Union
import urllib.parse
from bs4 import BeautifulSoup, NavigableString
from bs4.element import Tag
import requests
import pickle

from py_linq import Enumerable as E
import google.generativeai as genai
from browser_cookie3 import http
import numpy as np

from .detector import Config
from .transcriber import Transcription
from . import utils

#from matplotlib.axes import Axes

search_engines = {
    "google": {
        "url": "https://www.google.co.jp/search?hl=jp&gl=JP&",
        "query": "q",
        "container": ["div", {"id": "main"}]
    },
    "bing": {
        "url": "https://www.bing.com/search?",
        "query": "q",
        "container": ["ol", {"id": "b_results"}]
    }
}

def search(word: str, engine: str, cookie_jar = None) -> Union[Tag, NavigableString, None]:
    search_engine = search_engines[engine]
    search_url = search_engine["url"]
    query_key: str = search_engine["query"]
    query = urllib.parse.urlencode({query_key: word})
    search_url += query

    if not cookie_jar:
        user_agent = "(｀・ω・´)"  # not to load images(?)
        headers = {'User-Agent': user_agent.encode()}
        response = requests.get(search_url, headers=headers)
    else:
        #Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0
        # User-Agentを設定
        session = requests.Session()
        session.headers.update({
            #'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"
        })
        session.cookies.update(cookie_jar)

        # リクエストを送信
        response = session.get(search_url)

    response.raise_for_status()
    html = response.text#content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find(*search_engine["container"])#.prettify()

def get_items_google(tag: Tag) -> List[str]:
    child_divs = tag.find_all('div', recursive=False)

    result_divs = [child_div for child_div in child_divs if child_div.find('h3')]
    result_divs = [div.find("h3").find("div") for div in result_divs]
    result_divs = [div for div in result_divs if not div.find("span")]

    return [div.text for div in result_divs]

def get_items_bing(tag: Tag) -> List[str]:
    # b_algo
    child_lis = tag.find_all('li', recursive=False)

    result_lis = [child_li for child_li in child_lis if child_li.find('h2')]
    result_lis = [li.find("h2").find("a") for li in result_lis]
    #result_lis = [a for a in result_lis if not a.find("span")]

    return [a.text for a in result_lis if a]

def find_min_repetition(s):
    # 正規表現を使用して繰り返しパターンを検出
    pattern = re.compile(r"(.+?)\1+")
    match = pattern.search(s)

    if match:
        repetition = match.group(1)
        return repetition, match
    else:
        return s, match

class Identifier:

    def __init__(self, engine_type: str, transcriptions: List[Transcription], model: genai.GenerativeModel, config: Config, prompt: str="", cookie_jar: http.cookiejar.CookieJar = None):
        self.engine_type = engine_type
        self.model = model
        self.config = config
        self.transcriptions = transcriptions

        self.output_dir = self.config.output_dir / self.config.input_path.stem
        self.prepare()

        self.prompt = """
Guess the artist and the song name in human understandable Japanese as possible as you can from the list and return it in json format include "artist" and "title" as keys.
If you can't identify them uniquely, the use top item of list that include the word "歌詞".

{}
""" if not prompt else prompt
        self.cookie_jar = cookie_jar


    def prepare(self,):
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)

    def do_cache(self, transcribes: List[Transcription]):
        finished = False
        while not finished:
            try:
                with open(self.output_dir / f"{self.config.input_path.stem}.pkl", "wb") as h:
                    pickle.dump(transcribes, h)
                finished = True
            except pickle.PicklingError:
                transcribes = [Transcription.Renew(t) for t in transcribes]


    def get_search_word(self, transcription: Transcription):

        text = transcription.text

        while True:
            total_len = len(text)
            idx = total_len // 2
            search_word = text[idx:(idx+self.config.thres_set.search_len)]

            min_rep, match = find_min_repetition(search_word)

            if match is None:
                break
            else:
                start, end = match.span()
                if end - start < total_len/4: # FIXME: fixed value?
                    break

            text = text[:start] + min_rep + text[end:]

        return search_word

    def guess_song(self, transcription: Transcription):
        self.cache_hit = False

        segment = transcription.segment
        if segment[1] - segment[0] < self.config.thres_set.transc_long_thres:
            return {}

        
        # search lyrics
        if not transcription.search_result:
            search_word = self.get_search_word(transcription)
            tags = search(search_word, self.engine_type, self.cookie_jar)
            items = (globals()[f"get_items_{self.engine_type}"])(tags)

            transcription.search_word = search_word
            transcription.search_result = items

        else:
            items = transcription.search_result
            self.cache_hit = True
        

        prompt = self.prompt.format(str.join("\n", items))

        # guess song from search result
        if not transcription.llm_result:
            response = self.model.generate_content(prompt)
            llm_result = ""
            if len(response.parts):
                llm_result = response.parts[0].text
                transcription.llm_result = llm_result
        else:
            llm_result = transcription.llm_result
            self.cache_hit = True
        

        try:
            json_data = json.loads(re.search(r"\A```(?:json)?(.*)```\Z", llm_result, re.MULTILINE | re.DOTALL)[1])
        except (json.JSONDecodeError, TypeError) as e:
            #print(f"JSON decoding error: {e}")
            json_data = {}

        if json_data:
            transcription.artist = json_data["artist"]
            transcription.title = json_data["title"]
        else:
            transcription.artist = ""
            transcription.title = ""
        
        return transcription

    def main(self, resumed_trsc: List[Transcription] = []) -> List[Transcription]:

        resume_mode = not not resumed_trsc

        if resume_mode:
            self.transcriptions = resumed_trsc

        try:
            for idx, transcription in enumerate(self.transcriptions):
                if resume_mode and transcription.title:
                    print(f"Skip Guess {idx}: {transcription.title}/{transcription.artist}")
                else:
                    self.guess_song(transcription)

                    print(f"Guessed {idx}: {transcription.title}/{transcription.artist}")
                    if not self.cache_hit:
                        time.sleep(5)

            self.do_cache(self.transcriptions)
        except Exception as ex:
            print("Err", ex, "do cache.")
            self.do_cache(self.transcriptions)
            raise ex

        return self.transcriptions


    def get_cache(self) -> List[Transcription]:
        return utils.load_pickle(self.output_dir / f"{self.config.input_path.stem}.pkl")

    def save_csv(self, media_dir: pathlib.Path, soundfile: pathlib.Path, identified: List[Transcription], end_expand = 5.0, name_filter = None):

        if name_filter is not None and not name_filter(soundfile):
            print("Skip csv", soundfile.name)
            # continue
            return
        else:
            print("Write csv", soundfile.name)

        csv_file = media_dir / "identified" / soundfile.stem / f"{soundfile.stem}.csv"
        csv_data = []

        transcriptions: List[Transcription] = identified

        for idx, transcription in enumerate(transcriptions):
            title = transcription.title
            #print(title, transcription.search_word)
            if not title:
                title = "NoName" + str(idx)

            start, end = transcription.segment
            end += end_expand

            csv_data.append([start, end, title, transcription.artist])

        with open(csv_file, "w", newline="") as file:
            mywriter = csv.writer(file, delimiter=",")
            mywriter.writerows(np.array(csv_data))