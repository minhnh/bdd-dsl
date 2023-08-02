# SPDX-License-Identifier:  GPL-3.0-or-later
import re
import signal
from bdd_dsl.exception import GracefulExit


FILENAME_REPLACEMENTS = {" ": "_", ":": "__", "/": "_"}
VAR_NAME_REPLACEMENTS = {"-": "_"}
VAR_NAME_REPLACEMENTS.update(FILENAME_REPLACEMENTS)

__FILE_LOADER_CACHE = {}


def __read_file_and_cache(filepath: str) -> str:
    """
    Caching string contents of files for quick access and reducing IO operations.
    May need "forgetting" mechanism if too many large files are stored. Should be fine
    for loading JSON metamodels and SHACL constraints in Turtle format.
    """
    if filepath in __FILE_LOADER_CACHE:
        return __FILE_LOADER_CACHE[filepath]

    with open(filepath) as infile:
        file_content = infile.read()
    __FILE_LOADER_CACHE[filepath] = file_content
    return file_content


def get_valid_name(name: str, replacement_dict: dict) -> str:
    """
    based on same function from https://github.com/django/django/blob/main/django/utils/text.py
    also convert ':' to '__' and '/' to '_'

    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'
    """
    s = str(name).strip()
    for char in replacement_dict:
        s = s.replace(char, replacement_dict[char])

    # remove remaining characters
    s = re.sub(r"(?u)[^-\w.]", "", s)
    if s in {"", ".", ".."}:
        # suspicious file name
        raise ValueError(f"Could not derive file name from '{name}'")
    return s


def get_valid_filename(name: str) -> str:
    return get_valid_name(name, FILENAME_REPLACEMENTS)


def get_valid_var_name(name: str) -> str:
    return get_valid_name(name, VAR_NAME_REPLACEMENTS)


def raise_graceful_exit_handler(signum, frame):
    raise GracefulExit(signum)


def register_termination_signals(handled_signals=[signal.SIGINT, signal.SIGTERM]):
    for signum in handled_signals:
        signal.signal(signum, raise_graceful_exit_handler)
