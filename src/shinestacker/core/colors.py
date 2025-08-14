# pylint: disable=C0114, C0116
COLORS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "light_grey": 37,
    "dark_grey": 90,
    "light_red": 91,
    "light_green": 92,
    "light_yellow": 93,
    "light_blue": 94,
    "light_magenta": 95,
    "light_cyan": 96,
    "white": 97,
}

BG_COLORS = {
    "bg_black": 40,
    "bg_red": 41,
    "bg_green": 42,
    "bg_yellow": 43,
    "bg_blue": 44,
    "bg_magenta": 45,
    "bg_cyan": 46,
    "bg_light_grey": 47,
    "bg_dark_grey": 100,
    "bg_light_red": 101,
    "bg_light_green": 102,
    "bg_light_yellow": 103,
    "bg_light_blue": 104,
    "bg_light_magenta": 105,
    "bg_light_cyan": 106,
    "bg_white": 107,
}

EFFECTS = {
    "bold": 1,
    "dark": 2,
    "italic": 3,
    "underline": 4,
    "blink": 5,
    "reverse": 7,
}


def color_str(text, *args):
    text_colored = text
    for arg in args:
        if arg in COLORS:
            text_colored = f"\033[{COLORS[arg]}m{text_colored}"
        elif arg in BG_COLORS:
            text_colored = f"\033[{BG_COLORS[arg]}m{text_colored}"
        elif arg in EFFECTS:
            text_colored = f"\033[{EFFECTS[arg]}m{text_colored}"
        else:
            raise ValueError(f"Color or effect not supported: {arg}")
    return text_colored + "\033[0m"
