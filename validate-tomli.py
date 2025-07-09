import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib


def validate(file):
    try:
        with open(file, 'rb') as f:
            tomllib.load(f)
        print(f"✅ '{file}' is valid")
        return True
    except Exception as e:
        print(f"❌ Error in '{file}': {e}")
        return False


if __name__ == "__main__":
    validate(sys.argv[1] if len(sys.argv) > 1 else 'pyproject.toml')
