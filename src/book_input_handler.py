from internetarchive import get_item
from pydantic import HttpUrl
from typing import Union, Optional, List, Dict
from validators import url
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup
import httpx
from pathlib import Path
import os
import yaml
import json
import re
from ai_book_processing import chain_functions


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


def process_tab_delimited_file(directory_name: Path) -> list[dict[str, str]]:
    """
    This function processes a # separated markdown file and returns a list of dicts.

    This markdown file is the first rough version of the edit, where the book publisher separates
    paragraphs and removes the page numbers and other metadata that will not contribute to the
    final reading of the Audiobook.

    :param directory_name: The path to the markdown file.
    :type directory_name: Path
    :return: A list of dictionaries containing processed paragraphs and metadata.
    :rtype: list[dict[str, str]]
    """

    directory_name = Path(directory_name)
    book_name = directory_name.stem

    with open(directory_name, 'r', encoding='utf-8') as file:
        file_contents = file.read()

    file_contents = file_contents.replace('*', ' ')
    items = re.split(r'#', file_contents)
    items = [item.replace('\n', ' ').replace('\t', ' ').replace('\\', ' or ').replace('/', ' or ').strip() for item in items]
    items = [item for item in items if item]
    items = [re.sub(r'\s+', ' ', item) for item in items]

    result = [{'bookname': book_name, 'partext': item, 'paragraphnum': i} for i, item in enumerate(items, 1)]

    # Extract the base file name without extension
    base_filename = os.path.splitext(os.path.basename(directory_name))[0]

    # Create a YAML output file with the same base name
    output_path = os.path.join(os.path.dirname(directory_name), f"{base_filename}.yaml")
    with open(output_path, 'w', encoding='utf-8') as yaml_file:
        yaml.dump(result, yaml_file, default_flow_style=False)

    return result


def save_markdown_json(directory_name: Path) -> List[Dict[str, str]]:
    """
    Save processed paragraphs to a JSON file for further use.

    This function takes a list of dictionaries containing processed paragraph data and saves them to a JSON file one by one.
    As each paragraph is completed with the editing process, it appends to this file along with the line number.
    The resulting JSON file will be used as input by the `generate_voice` function.

    :param directory_name: The path to the directory containing the markdown files.
    :type directory_name: Path
    :return: A list of dictionaries containing the saved processed paragraphs.
    :rtype: List[Dict[str, str]]
    """
    directory_path = Path(directory_name)

    book_name = directory_path.stem
    output_path = directory_path.parent.joinpath(book_name).with_suffix('.json')

    result = process_tab_delimited_file(directory_name)

    with open(output_path, 'w', encoding='utf-8') as json_file:
        for eachpar in result:
            eachpar['partext'] = chain_functions(eachpar['partext'])

            print(f"Cleaned text {eachpar.get('partext')}")
            # Append each dictionary as a separate JSON entry
            json.dump(eachpar, json_file)
            json_file.write("\n")  # Newline to separate JSON entries
            # "Write to JSON file"

    return load_json_file(output_path)


def load_json_file(file_path: Path) -> Optional[List[Dict[str, str]]]:
    """
    Load a JSON file containing processed paragraph data.

    This function reads a JSON file, which is created from the original raw edited markdown file,
    and returns a list of dictionaries. Each dictionary represents a processed paragraph after
    being edited with an AI model.

    :param file_path: The path to the JSON file to be loaded.
    :type file_path: Path
    :return: A list of dictionaries containing processed paragraph data, or None on error.
    :rtype: Optional[List[Dict[str, str]]]
    """

    try:
        with open(file_path, 'r', encoding='utf-8') as json_file:
            data = [json.loads(line) for line in json_file]

            return data

    except Exception as e:
        print(f"Error while loading JSON file: {e}")
        return None

