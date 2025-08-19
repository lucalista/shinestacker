#!/bin/bash
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '/^blob/ {print $3,$4}' |
  sort -n -k1 |
  tail -50
