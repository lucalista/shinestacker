from focusstack.core.colors import color_str


def test_color():
    print(color_str('red', 'red'))
    print(color_str('green', 'green'))
    print(color_str('blue', 'blue'))
    print(color_str('black', 'black'))
    print(color_str('white', 'white'))
    assert True


def test_background():
    print(color_str('red', 'bg_red'))
    print(color_str('green', 'bg_green'))
    print(color_str('blue', 'bg_blue'))
    print(color_str('black', 'bg_black'))
    print(color_str('white', 'black', 'bg_white'))
    assert True


def test_effects():
    print(color_str('bold', 'white', 'bold'))
    print(color_str('italic', 'white', 'italic'))
    print(color_str('blink', 'white', 'blink'))
    assert True


if __name__ == '__main__':
    test_color()
    test_background()
    test_effects()
