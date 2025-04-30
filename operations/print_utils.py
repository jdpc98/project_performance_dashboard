# print_utils.py - Colored print utilities

def print_green(message):
    """Print a message in green color."""
    print("\033[92m" + str(message) + "\033[0m")

def print_red(message):
    """Print a message in red color."""
    print("\033[91m" + str(message) + "\033[0m")

def print_orange(message):
    """Print a message in orange/yellow color."""
    print("\033[93m" + str(message) + "\033[0m")

def print_cyan(message):
    """Print a message in cyan color."""
    print("\033[96m" + str(message) + "\033[0m")