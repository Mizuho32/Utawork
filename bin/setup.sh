#!/usr/bin/env bash

pip install -r ast/requirements.txt
pip install -r requirements.txt

w=ast/pretrained_models/audioset_10_10_0.4593.pth
if ! [ -f $w ]; then
  wget "https://www.dropbox.com/s/ca0b1v2nlxzyeb4/audioset_10_10_0.4593.pth?dl=1" -O $w
fi
