"""Imported first by every script: work from the repo root, so out/, models/, print/, ... resolve
the same whether you run `python3 cad/base.py` from the root or `python3 base.py` from cad/."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
