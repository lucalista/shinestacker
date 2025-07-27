project = 'Shine Stacker'
author = 'Luca Lista'
html_title = "Shine Stacker Documentation"

extensions = [
    'myst_parser',
    'sphinx.ext.mathjax'
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