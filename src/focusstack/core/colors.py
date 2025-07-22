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
    "black": 40,
    "red": 41,
    "green": 42,
    "yellow": 43,
    "blue": 44,
    "magenta": 45,
    "cyan": 46,
    "light_grey": 47,
    "dark_grey": 100,
    "light_red": 101,
    "light_green": 102,
    "light_yellow": 103,
    "light_blue": 104,
    "light_magenta": 105,
    "light_cyan": 106,
    "white": 107,
}

EFFECTS = {
    "bold": 1,
    "dark": 2,
    "italic": 3,
    "underline": 4,
    "blink": 5,
    "reverse": 7,
}


def color_str(text, color=None, background=None, attrs=None):
    text_colored = text
    if color is not None:
        color_code = COLORS[color]
        text_colored = f"\033[{color_code}m{text_colored}"
    if background is not None:
        bg_code = BG_COLORS[background]
        text_colored = f"\033[{bg_code}m{text_colored}"
    if attrs is not None:
        for attr in attrs:
            attr_code = EFFECTS[attr]
            text_colored = f"\033[{attr_code}m{text_colored}"
    return text_colored + "\033[0m"
