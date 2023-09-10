from datetime import datetime, date
from typing import Union, Optional, List, Dict, Set,Tuple
from urllib.parse import urlparse, quote
from httpx import RequestError
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, validator, Field, root_validator
from pydantic import HttpUrl
from internetarchive import get_item, item
from dateutil.parser import parse
from fuzzywuzzy import fuzz
import nltk
from nltk.corpus import words
from nltk.tokenize import word_tokenize



class ArchiveBook(BaseModel):
    """
    This is a Pydantic model for Archive.org books.

    This model represents the full metadata for a book on Archive.org.
    The model is based on the metadata returned by the Archive.org API.

    Attributes:
        identifier (str): The unique identifier of the book - Required / Primary Key.<br>
        collection (List[str]): List of collection names the book belongs to.<br>
        mediatype (Optional[str]): The type of media associated with the book.<br>
        scanner (Optional[str]): The scanner used for digitization.<br>
        title (Optional[str]): The title of the book.<br>
        uploader (Optional[str]): The uploader's name.<br>
        addeddate (datetime): Date when the book was added, with time set to midnight.<br>
        publicdate (datetime): Date when the book was made public, with time set to midnight.<br>
        description (Optional[str]): A brief description of the book.<br>
        creator (Optional[str]): The creator or author of the book.<br>
        source (Optional[str]): The source of the book.<br>
        date (datetime): Date associated with the book, with time set to midnight.<br>
        identifier_access (Optional[HttpUrl]): Access identifier URL.<br>
        identifier_ark (Optional[str]): ARK identifier.<br>
        ppi (Optional[str]): Pixels per inch information.<br>
        ocr (Optional[str]): OCR (optical character recognition) information.<br>
        repub_state (Optional[str]): Republishing state information.<br>
        backup_location (Optional[str]): Location of backup.<br>
        external_identifier (Optional[str]): External identifier of the book.<br>
        text_file (Optional[str]): Text file associated with the book.<br>
        text_url (Optional[HttpUrl]): URL to the text content.<br>
        text_content (Optional[List[Dict[str, str]]]): List of dictionaries containing text content data.<br>
        access_restricted_item (Optional[Union[bool, str]]): Information about access restrictions.<br>

    Methods:
        parse_and_format_datetime(value, field):
            A validator method to parse and format datetime values.

    Raises:
        ValueError: If there is an issue with datetime parsing or formatting.
    """
    identifier: str
    collection: Optional[List[str]]
    mediatype: Optional[str]
    scanner: Optional[str]
    title: Optional[str]
    uploader: Optional[str]
    addeddate: datetime = datetime.today().replace(microsecond=0)
    publicdate: datetime = datetime.today().replace(microsecond=0)
    description: Union[Optional[str], List[str]]
    creator: Optional[str]
    source: Optional[str]
    date: datetime = datetime.today().replace(microsecond=0)
    identifier_access: Optional[HttpUrl] = Field(alias="identifier-access")
    identifier_ark: Optional[str] = Field(alias="identifier-ark")
    ppi: Optional[str]
    ocr: Optional[str]
    repub_state: Optional[str] = Field(alias="repub-state")
    backup_location: Optional[str] = Field(alias="backup-location")
    external_identifier: Union[Optional[str], List[str]] = Field(alias="external-identifier")
    text_file: Optional[str] = Field(alias="text-file")
    text_url: Optional[HttpUrl] = Field(alias="text-url")
    text_content: Optional[List[Dict[str, str]]] = Field(alias="text-content")
    access_restricted_item: Optional[Union[bool, str]] = Field(alias="access-restricted-item")

    @validator("addeddate", "publicdate", "date", pre=True, always=True)
    def parse_and_format_datetime(cls, value, field):
        """Parse and format datetime values,  that come from the source object.
           Returns a datetime object with time set to midnight."""

        if isinstance(value, datetime):
            formatted_datetime = value.replace(hour=0, minute=0, second=0, microsecond=0)
            return formatted_datetime
        if isinstance(value, str):
            parsed_date = parse(value)
            formatted_datetime = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
            return formatted_datetime
        raise ValueError(f"Invalid value for {field.name}")

    @validator("description", "external_identifier")
    def convert_list_to_string(cls, value):
        """Convert list values to strings."""
        if isinstance(value, list):
            return ' '.join(value)
        return value

    @validator("title", "creator")
    def convert_to_title_case(cls, value):
        """Convert text to Title Case."""

        if isinstance(value, str):
            return value.title()
        return value


def get_archiveorg_item(archive_identifier: Union[HttpUrl, str]) -> item:
    """
    Retrieve the base item of an Archive.org item.

    Args:
        archive_identifier (Union[HttpUrl, str]): The URL or identifier of the Archive.org item.

    Returns:
        item: The base item of the Archive.org item.

    This function fetches the base item of an Archive.org item from a provided URL or identifier.
    It checks for the standard location of the identifier first, and if not found, looks in the second location.

    Examples:
        ```python
        archive_identifier = 'https://archive.org/details/MagisterLudi-TheGlassBeadGame-HermanHesse/hesperian-environment-health/'
        item = get_archiveorg_item(archive_identifier)
        print(item)
        ```
    """

    new_identifier = archive_identifier
    if 'details' in archive_identifier:
        new_identifier = urlparse(archive_identifier).path.split('/')[-1]
    elif 'stream' in archive_identifier:
        new_identifier = urlparse(archive_identifier).path.split('/')[2]

    meta_item = get_item(new_identifier)

    if not meta_item.identifier:

        archive_identifier = urlparse(archive_identifier).path.split('/')[-3]
        meta_item = get_item(archive_identifier)

    return meta_item


def get_archiveorg_metadata(archive_identifier: Union[HttpUrl, str]) -> ArchiveBook:
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
    archiveorglinkg = get_archiveorg_metadata('https://archive.org/details/in.ernet.dli.2015.280019')
    indentifierint = get_archiveorg_metadata('in.ernet.dli.2015.280019')
    archiveorgtextlink = get_archiveorg_metadata('http://archive.org/stream/in.ernet.dli.2015.280019/2015.280019.Essays-By_djvu.txt')

        ```
    Note:
        This function accesses Archive.org resources to retrieve metadata. It checks for access restrictions
        and raises a ValueError if metadata access is restricted.
    """

    meta_item = get_archiveorg_item(archive_identifier)

    # This will convert the dict items to a list in order to identify the text file.
    files = list(meta_item.get_files())
    try:
        textfile = [file for file in files if file.format == 'DjVuTXT'][0].metadata.get('name')
    except IndexError:
        textfile = ''

    metadict = meta_item.metadata.items()
    archive_book = ArchiveBook(**dict(metadict))

    archive_book.text_file = textfile

    if archive_book.access_restricted_item:
        raise ValueError("Access to metadata is restricted.")

    try:
        archive_book.text_url = f"{archive_book.identifier_access}/{quote(archive_book.text_file)}".replace('details','stream')
        archive_book.text_url = HttpUrl(archive_book.text_url, scheme="http")
    except ValueError as failed_text_url:
        raise ValueError(f'No text file found {failed_text_url}') from failed_text_url

    archive_book.description = ' '.join(BeautifulSoup(archive_book.description, 'lxml').stripped_strings)

    archive_book.text_file = textfile

    try:
        return archive_book
    except ValueError as val_error:
        raise ValueError(f"Error in parsing metadata: {val_error}") from val_error


def filter_strings_with_english_words(strings: List[str]) -> List[str]:
    """
    Filters a list of strings to return only those that contain at least one English word longer than 3 characters.
    Skips checking strings longer than 50 characters.

    :param strings: List of strings to be filtered.
    :return: List of filtered strings containing at least one English word longer than 3 characters.
    """
    filtered_strings = []
    english_words = set(words.words())

    for string in strings:
        # Skip checking strings longer than 50 characters
        if len(string) > 50:
            filtered_strings.append(string)
            continue  # Skip the rest of the loop for this string

        # Tokenize the string into words
        tokens = word_tokenize(string)

        # Check if any token is an English word longer than 3 characters
        if any(token.lower() in english_words and len(token) > 3 for token in tokens):
            filtered_strings.append(string)

    return filtered_strings


def find_similar_strings(strings: List[str], threshold: int = 60) -> Tuple[List[str], Set[str]]:
    """
    Find and remove similar strings in a list based on fuzzy similarity.

    :param strings: List of strings to compare.
    :param threshold: Similarity threshold. Strings with similarity above this value are considered similar.
    :return: A tuple containing a list of original strings with similar items removed, and a set of removed items.
    """
    similar_groups: List[List[str]] = []

    # Identify similar items
    for string in strings:
        found = False
        for group in similar_groups:
            if fuzz.ratio(string, group[0]) >= threshold:
                group.append(string)
                found = True
                break
        if not found:
            similar_groups.append([string])

    # Remove groups with 3 or more similar items
    items_to_remove = {item for group in similar_groups if len(group) >= 3 for item in group}

    # Remove items that are similar and non-English
    filtered_strings = [string for string in strings if string not in items_to_remove]
    filtered_strings = filter_strings_with_english_words(filtered_strings)

    return filtered_strings, items_to_remove

def merge_paragraphs(lines: List[str]) -> List[str]:
    """
    Merge lines into paragraphs based on sentence-ending punctuation.

    :param lines: List of lines to merge into paragraphs.
    :return: List of merged paragraphs.

    Example:
    >>> merge_paragraphs(["Hello, ", "world.", "How ", "are you?"])
    ['Hello, world.', 'How are you?']
    """
    paragraphs = []
    buffer = ""

    for line in lines:
        # Remove leading and trailing whitespaces
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        buffer += line + " "

        # Check if the line ends with sentence-ending punctuation
        if line[-1] in [".", "!", "?"]:
            paragraphs.append(buffer.strip())
            buffer = ""

    # Append any remaining content in the buffer
    if buffer:
        paragraphs.append(buffer.strip())

    return paragraphs


def return_archive_text(archive_identifier: Union[HttpUrl, str]) -> ArchiveBook:
    """
    Retrieve and return text content from an Archive.org identifier.

    Args:
        archive_identifier (str or HttpUrl):
            The identifier or URL for the Archive.org resource.

    Returns:
        ArchiveBook:
            An instance of the ArchiveBook class with the extracted data,
            or None if the data is not found.

    Raises:
        ValueError:
            If there is an issue accessing the text content or if the response is not valid.
    """
    try:
        archive_book = get_archiveorg_metadata(archive_identifier)
        text_url = archive_book.text_url

        response = httpx.get(text_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        pre_tag = soup.find("pre")

        if pre_tag:
            # Populate the ArchiveBook instance with additional data from the full text book,
            # identifier and text content
            #TODO First clean the list of paragraphs, and then assign to the text_content field
            #TODO Remove chapter or page headers that have many duplicate occurences
            #TODO Remove any text that is not part of the book, such as the Archive.org header and footer
            #TODO Remove lines with no English words, or only integers


            archive_book.text_content = pre_tag.string.split('\n\n')
            return archive_book

        # Raise an exception if pre_tag is missing
        raise ValueError("pre_tag is missing")

    except RequestError as request_error:
        error_message = f"Error accessing the text content: {request_error}"
        raise ValueError(error_message) from request_error

    except Exception as general_error:
        error_message = f"An error occurred while processing the text content: {general_error}"
        raise ValueError(error_message) from general_error


def test_return_archive_text() -> None:
    """Run a test on a few archive org links to make sure they work.
       Use a private link to make sure it fails and reports correctly.
       Also user a url with the identifier in the -3 location"""

    list_of_archive_books = [
        'https://archive.org/details/MagisterLudi-TheGlassBeadGame-HermanHesse/hesperian-environment-health/',
        'https://archive.org/details/Siddhartha-HermanHesse',
        'https://archive.org/details/philosophylitera0000port',  # This one is private and should fail
        'https://archive.org/details/ZiniSchopenhauer',
        'https://archive.org/details/schopenhauer-a.-sobre-la-voluntad-en-la-naturaleza-ocr-2003',
        'https://archive.org/details/in.ernet.dli.2015.191198']

    for archive_book in list_of_archive_books:
        try:
            return_archive_text(archive_book)
            print(f"Passed Test on {archive_book}")
        except ValueError as failed_test:
            print(f"Error for {archive_book}: {failed_test}")
