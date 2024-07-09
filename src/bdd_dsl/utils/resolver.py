# Inspired by https://github.com/comp-rob2b/kindyngen/ (kindyngen.utility.resolver)
# SPDX-License-Identifier: MPL-2.0
import pathlib
import urllib.request
import urllib.response
from email.message import EmailMessage


class IriToFileResolver(urllib.request.OpenerDirector):
    """
    A `urllib.request.OpenerDirector` that remaps specific URLs to local files.
    """

    def __init__(self, url_map: dict, download: bool = False):
        """
        A key-value pair in `url_map` specifies a prefix of a URL to a local location.
        For example, `{ "http://example.org/": "foo/bar/" }` would remap any urllib open request
        for any resource under "http://example.org/" to a local directory "foo/bar/".
        If the local file does not exist and `download` is True, attempt to download the file
        to the corresponding local location.
        """
        super().__init__()
        self.default_opener = urllib.request.build_opener()
        self.url_map = url_map
        self._download = download
        self._empty_header = EmailMessage()  # header expected by addinfourl

    def open(self, fullurl, data=None, timeout=None):
        assert isinstance(
            fullurl, urllib.request.Request
        ), f"expected URL of type 'urllib.request.Request', got type '{type(fullurl)}'"

        url = pathlib.Path(fullurl.full_url)

        # If the requested URL starts with any key in the url_map, fetch the file from a
        # local file that is derived from the URL and the value in the map
        for prefix, directory in self.url_map.items():
            if not url.is_relative_to(prefix):
                continue

            # Wrap the directory in a pathlib.Path to get access to convenience functions
            path = pathlib.Path(directory).joinpath(url.relative_to(prefix))

            # Download file if not exist in system and `download` is specified.
            # If `download` not specified, break from loop to open URL using default opener.
            if not path.exists():
                if not self._download:
                    break

                parent_path = path.parent
                if not parent_path.exists():
                    parent_path.mkdir(parents=True)
                assert parent_path.is_dir(), f"not a directory: {parent_path}"

                with self.default_opener.open(fullurl.full_url) as url_data:
                    with path.open("wb") as cache_file:
                        cache_file.write(url_data.read())
                assert path.exists(), f"File '{path}' not cached for URL '{fullurl.full_url}'"

            # Open the file and wrap it in an urllib response
            fp = path.open("rb")
            resp = urllib.response.addinfourl(
                fp, headers=self._empty_header, url=fullurl.full_url, code=200
            )
            return resp

        # If we did not find any match above just continue with the default opener
        # which has the behaviour as initially expected by rdflib.
        return self.default_opener.open(fullurl, data, timeout)


def install(resolver):
    """
    Note that only a single opener can be globally installed in urllib. Only the
    latest installed resolver will be active.
    """
    urllib.request.install_opener(resolver)
