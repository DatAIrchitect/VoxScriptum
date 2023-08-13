from internetarchive import get_item
from pydantic import HttpUrl
from typing import Union, Optional
from validators import url
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
import httpx


def get_archiveorg_metadata(archive_identifier: Union[HttpUrl, str]) -> dict[str, str]:
    """
    Return metadata from an Archive.org identifier.
    This takes a standard Archive org identifier and returns a dictionary containing metadata about the resource.
    The identifier can be a URL from archive.org or a string of the identifier.
    If a URL is passed, the function will extract the identifier from the URL.

    Args:
        archive_identifier (Union[HttpUrl, str]):
            The identifier for the Archive.org resource. It can be an archive.org URL or a string.
    Returns:
        dict[str, str]:
            A dictionary containing metadata about the Archive.org resource.
    Raises:
        ValueError:
            If metadata access is restricted.
    Example:
        You can use this function to retrieve metadata from an Archive.org identifier:

        ```python
    # Three different acceptable inputs:
    archiveorglinkg = return_archiveorg_meta('https://archive.org/details/in.ernet.dli.2015.280019')
    indentifierint = return_archiveorg_meta('in.ernet.dli.2015.280019')
    archiveorgtextlink = return_archiveorg_meta('http://archive.org/stream/in.ernet.dli.2015.280019/2015.280019.Essays-By_djvu.txt')

        ```
    Note:
        This function accesses Archive.org resources to retrieve metadata. It checks for access restrictions
        and raises a ValueError if metadata access is restricted.
    """

    if url(archive_identifier):
        if 'details' in archive_identifier:
            archive_identifier = urlparse(archive_identifier).path.split('/')[-1]
        elif 'stream' in archive_identifier:
            archive_identifier = urlparse(archive_identifier).path.split('/')[2]

    item = get_item(archive_identifier)

    files = list(item.get_files())

    try:
        textfile = [file for file in files if file.format == 'DjVuTXT'][0].metadata.get('name')
    except TypeError:
        textfile = ''

    metadict = dict(item.metadata.items())

    if metadict.get('access-restricted-item'):
        raise ValueError("Access to metadata is restricted.")

    metadict['description'] = ' '.join(BeautifulSoup(metadict.get('description'), 'lxml').stripped_strings)

    if textfile:
        metadict['text_file'] = textfile
        metadict['text_url'] = f"{metadict.get('identifier-access')}/{quote(metadict.get('text_file'))}".replace('details', 'stream')

    return metadict


def return_archive_text(archive_identifier: Union[HttpUrl, str]) -> Optional[str]:
    """
    Retrieve and return text content from an Archive.org identifier.
    Args:
        archive_identifier (str):
            The identifier for the Archive.org resource. It can be an identifier or archive.org url
    Returns:
        Optional[str]:
            The extracted text content from the Archive.org resource, or None if not found.
    Raises:
        ValueError:
            If there is an issue accessing the text content or if the response is not valid.
    Example:
        You can use this function to retrieve text content from an Archive.org identifier:

        ```python
    text_content = return_archive_text('https://archive.org/details/in.ernet.dli.2015.280019')
        ```

    Note:
        This function retrieves text content from Archive.org resources. It uses the provided identifier
        to access the text content and returns it. If the text content cannot be found or there is an issue
        with the retrieval, None is returned.
    """
    try:
        full_archive = get_archiveorg_metadata(archive_identifier)
        text_url = full_archive.get('text_url')

        response = httpx.get(text_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        pre_tag = soup.find("pre")

        if pre_tag:
            return pre_tag.string
        else:
            return None

    except httpx.RequestError as e:
        raise ValueError(f"Error accessing the text content: {e}")
    except Exception as e:
        raise ValueError(f"An error occurred while processing the text content: {e}")

