# SPDX-License-Identifier:  GPL-3.0-or-later
import re
import signal
from socket import _GLOBAL_DEFAULT_TIMEOUT
import urllib.request
from importlib.metadata import version

import numpy as np

from bdd_dsl.exception import GracefulExit


__FILENAME_REPLACEMENTS = {" ": "_", ":": "__", "/": "_"}
__VAR_NAME_REPLACEMENTS = {"-": "_"}
__VAR_NAME_REPLACEMENTS.update(__FILENAME_REPLACEMENTS)

__FILE_LOADER_CACHE = {}
__URL_CONTENT_CACHE = {}

BDD_DSL_VERSION = version("bdd-dsl")


def read_file_and_cache(filepath: str) -> str:
    """Read and cache string contents of files for quick access and reducing IO operations.

    May need "forgetting" mechanism if too many large files are stored. Should be fine
    for loading JSON metamodels and SHACL constraints in Turtle format.
    """
    if filepath in __FILE_LOADER_CACHE:
        return __FILE_LOADER_CACHE[filepath]

    with open(filepath) as infile:
        file_content = infile.read()

    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8")

    __FILE_LOADER_CACHE[filepath] = file_content
    return file_content


def read_url_and_cache(url: str, timeout=_GLOBAL_DEFAULT_TIMEOUT) -> str:
    """Read and cache text responses from URL

    `timeout` specifies duration in seconds to wait for response. Only works for HTTP, HTTPS & FTP.
    By default `socket._GLOBAL_DEFAULT_TIMEOUT` will be used, which usually means no timeout.
    """
    if url in __URL_CONTENT_CACHE:
        return __URL_CONTENT_CACHE[url]

    with urllib.request.urlopen(url, timeout=timeout) as f:
        url_content = f.read()

    if isinstance(url_content, bytes):
        url_content = url_content.decode("utf-8")

    __URL_CONTENT_CACHE[url] = url_content
    return url_content


def get_valid_name(name: str, replacement_dict: dict) -> str:
    """Return the given string converted to a string that can be used for a clean filename.

    Based on same function from https://github.com/django/django/blob/main/django/utils/text.py
    also convert ':' to '__' and '/' to '_'

    Remove leading and trailing spaces; convert other spaces to underscores;
    and remove anything that is not an alphanumeric, dash, underscore, or dot.
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
    return get_valid_name(name, __FILENAME_REPLACEMENTS)


def get_valid_var_name(name: str) -> str:
    return get_valid_name(name, __VAR_NAME_REPLACEMENTS)


def raise_graceful_exit_handler(signum, frame):
    raise GracefulExit(signum)


def register_termination_signals(handled_signals=[signal.SIGINT, signal.SIGTERM]):
    for signum in handled_signals:
        signal.signal(signum, raise_graceful_exit_handler)


def check_or_convert_ndarray(in_array) -> np.ndarray:
    if isinstance(in_array, np.ndarray):
        return in_array

    if isinstance(in_array, list) or isinstance(in_array, tuple):
        return np.array(in_array)

    raise ValueError(
        f"input of type '{type(in_array)}' is not an instance numpy.ndarray and cannot be converted into one."
    )
