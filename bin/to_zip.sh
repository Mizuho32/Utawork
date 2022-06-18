#!/usr/bin/env bash

if ! [ -d out ]; then
  mkdir out
fi

rm out/*.zip out/*.rev

git archive HEAD --output=out/recog.zip
git rev-parse --short HEAD > out/recog.rev

cat out/recog.rev
git rev-parse --short HEAD

cd ast
git archive HEAD --output=../out/ast.zip
git rev-parse --short HEAD > ../out/ast.rev

