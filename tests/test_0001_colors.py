from focusstack.core.colors import color_str


def test_color():
	print(color_str('red', 'red'))
	print(color_str('green', 'green'))
	print(color_str('blue', 'blue'))
	print(color_str('black', 'black'))
	print(color_str('white', 'white'))
	assert True


def test_background():
	print(color_str('red', background='red'))
	print(color_str('green', background='green'))
	print(color_str('blue', background='blue'))
	print(color_str('black', background='black'))
	print(color_str('white', 'black', background='white'))
	assert True


def test_effects():
	print(color_str('bold', 'white', attrs=['bold']))
	print(color_str('italic', 'white', attrs=['italic']))
	print(color_str('blink', 'white', attrs=['blink']))
	assert True


if __name__ == '__main__':
	test_color()
	test_background()
	test_effects()
