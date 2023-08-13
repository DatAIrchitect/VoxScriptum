from marvin.openai import openai_fn,OpenAIFunctionRegistry
import marvin
from marvin import ai_classifier,ai_fn,ai_model,AIApplication
import unicodedata
import builtins
import re
from bs4 import BeautifulSoup
from spellchecker import SpellChecker
from typing import Callable, List, Optional, Union, Any


def modify_return(*modifiers: Union[str, Callable],
                  mode: str = 'all') -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Apply one or more modifiers to the return value of a function.
    Chain a series of functions to a value, and return the result.

    Args:
        modifiers (Union[str, Callable]): One or more modifier functions or their names.
        mode (str, optional): Mode of operation. Can be 'all', 'stop_on_success', or 'stop_on_failure'.
            Defaults to 'all'.

    Returns:
        Callable[[Callable], Callable]: Decorator function to modify the return value of a given function.
    """

    valid_modes = {'all', 'stop_on_success', 'stop_on_failure'}
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode '{mode}'. Mode must be one of {', '.join(valid_modes)}.")

    def decorator(func: Callable) -> Callable:
        def apply_modifier(result: Any, modifier: Union[str, Callable]) -> Any:
            if callable(modifier):
                return modifier(result)
            elif isinstance(modifier, str):
                modifier_func = globals().get(modifier) or locals().get(modifier) or getattr(builtins, modifier, None)
                if callable(modifier_func):
                    return modifier_func(result)
            raise ValueError(f"Invalid modifier '{modifier}'. Expected a function or function name.")

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            for modifier in modifiers:
                try:
                    result = apply_modifier(result, modifier)
                    if mode == 'stop_on_success':
                        break
                except Exception as e:
                    if mode == 'stop_on_failure':
                        break
                    print(f"Function '{modifier}' failed with error: {e}")
                    continue
            return result

        return wrapper

    return decorator


@ai_fn
def prepare_audiobook(partext: str) -> str:
    """
    You are a professional book editor, and you are preparing a book
    that has been scanned from an OCR for for Audiobook production.
    The Audiobook will be created by an AI, and it reads everything literally.

    You should not change the text, or add any text of your own!

    You should find all spelling errors, and correct the spelling based
    on the local text context, and your best estimation.

    Remove - hyphens in words, and replace the hyphen with a space only.

    You should find hyphenated words, and you should move the
    first part of the word to the next line, and remove the -

    You should remove all characters that will not be easily read by the AI narrator,
    such as * - or / or \ or #, and other characters that do not directly contribute
    to the meaning of the text, replace these characters with a space.

    You should replace abbreviations with the full word, such as Mr. with Mister, or Dr. with Doctor.

    You should add punctuation, where it is necessary for a better reading experience,

    Where there are words or characters that cannnot be fixed without any suitable alternative,
    then replace them with ' ' or determine the best word, only if it does not change the
    meaning or the reading of the text sufficiently.

    Double check your work before returning the text!

    If there is an error then return ''
    """


@ai_fn
def edit_audiobook(partext: str) -> str:
    """Review a paragraph that is being prepared for an audiobook reading, and fix any grammatical,
       or spelling errors. There are spelling errors in this text, and they should be fixed with your best estimate
       of the proper words."""


def find_misspelled_words(text: str) -> List[str]:
    """
    Find and return a list of misspelled words in the given text.
    Args:
        text (str): The input text to find misspelled words in.
    Returns:
        List[str]: A list of misspelled words found in the input text.
    """

    # 'The function \'FormatResponse\' encountered an error: invalid syntax.
    # Perhaps you forgot a comma? ( , line 2) The payload you provided was: { "data":
    # } You can try to fix the error and call the function again.
    # [re for re in res if 'function' in re.get('partext')]

    text_cleaned = re.sub(r'[^a-zA-Z0-9\s.]', ' ', text)

    # Create a SpellChecker object
    spell = SpellChecker()

    words = re.findall(r'\S+', text_cleaned)

    misspelled_words = [word for word in words if word.lower() not in spell]

    return misspelled_words


def clean_and_chain(text_in: str) -> str:
    """
    Clean and process input text using various operations.
    Args:
        text_in (str): The input text to be cleaned and processed.
    Returns:
        str: The cleaned and processed text.
    """
    try:
        text_in = ' '.join(list(BeautifulSoup(text_in, 'lxml').stripped_strings))
    except:
        pass

    try:
        text_clean_compile = re.compile('<.*?>')
        clntxt = re.sub(text_clean_compile, '', text_in)
        clntxt = unicodedata.normalize("NFKD", clntxt)
        clntxt = re.sub(r'[^\x00-\x7F]+', ' ', clntxt)
        clntxt = clntxt.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ').replace('&nbsp;', ' ').replace('&amp;', '&').replace('-', ' ')
        clntxt = re.sub(r'\s{2,}', ' ', clntxt)
        clntxt = f"{clntxt} ....."
    except:
        return text_in

    return clntxt.strip()


@modify_return('prepare_audiobook', clean_and_chain)
def chain_functions(clean_paragraph: str) -> str:
    """
    Apply a series of functions to a clean paragraph.

    Args:
        clean_paragraph (str): The input paragraph.

    Returns:
        str: The modified paragraph after applying functions.
    """
    spelling_errors = find_misspelled_words(clean_paragraph)

    if spelling_errors:
        clean_paragraph = edit_audiobook(clean_paragraph)
        return clean_paragraph
    else:
        return clean_paragraph




