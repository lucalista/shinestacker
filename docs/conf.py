import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

project = 'Shine Stacker'
author = 'Luca Lista'
html_title = "Shine Stacker Documentation"

extensions = [
    'myst_parser',
    'sphinx.ext.mathjax',
]

myst_enable_extensions = [
    "dollarmath",
    "amsmath",
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

master_doc = 'index'

html_theme = 'furo'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '**/.ipynb_checkpoints']

autosummary_generate = True
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}
