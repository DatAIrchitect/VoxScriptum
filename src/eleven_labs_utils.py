from env_variables import ELEVENLABSKEY
from elevenlabs import (
    clone, generate, play, set_api_key, save, Voice, VoiceDesign,
    Gender, Age, Accent
)
from elevenlabs.api import History, Voices
from typing import List

set_api_key(ELEVENLABSKEY)


def return_history() -> History:
    """
    Return an ElevenLabs history object from the account API.

    :return: An ElevenLabs history object containing account history.
    :rtype: History
    """

    history = History.from_api()

    return history


def design_voice(voice_name: str, read_text: str = "This is a test for a new designed voice.",):
    """
        Design a voice for ElevenLabs API.

        :param voice_name: The name for the designed voice.
        :type voice_name: str
        :param read_text: The text to use for designing the voice. Defaults to a test sentence.
        :type read_text: str
        """

    design = VoiceDesign(
        name=voice_name,
        text=read_text,
        gender=Gender.female,
        age=Age.old,
        accent=Accent.british,
        accent_strength=1.7)

    # Generate audio from the design, and play it to test if it sounds good (optional)
    audio = design.generate()
    play(audio)

    # Convert design to usable voice
    Voice.from_design(design)


def return_voices() -> List[dict[str, str]]:
    """
    Return all ElevenLabs voices from the account API.

    This function retrieves a list of all available voices from the ElevenLabs account API. Each voice's ID and name are extracted and returned as a list of dictionaries.

    :return: A list of dictionaries containing voice IDs and names.
    :rtype: List[dict[str, str]]
    """
    voices = Voices.from_api()

    return [{'voice_id': voice.voice_id, 'voice_name': voice.name} for voice in voices]


def clone_voice(voice_sample: str, description: str, voice_name: str) -> Voice:
    """
    Clone a voice from a voice sample for ElevenLabs API.

    :param voice_sample: The path to the voice sample file to use for cloning.
    :type voice_sample: str
    :param description: The description for the cloned voice.
    :type description: str
    :param voice_name: The name for the cloned voice.
    :type voice_name: str
    :return: The cloned voice object.
    :rtype: Voice
    """
    voice = clone(
        name=voice_name,
        description=description,
        files=[voice_sample])

    return voice


def generate_voice(voice: str, voice_text: str, to_save: bool = False, savefile: Union[Path, str] = None) -> Union[bytes, None]:
    """
    Generate audio from text using a specified voice for ElevenLabs API.

    :param voice: The name of the voice to use for generating audio.
    :type voice: str
    :param voice_text: The text to convert into audio.
    :type voice_text: str
    :param to_save: Whether to save the generated audio to a file. Defaults to False.
    :type to_save: bool
    :param savefile: The path to save the audio file (required if `to_save` is True).
    :type savefile: Path
    :return: The generated audio data as bytes, or None if saving to file.
    :rtype: Union[bytes, None]
    """

    audio = generate(text=voice_text, voice=voice)

    if to_save:
        save(audio=audio, filename=savefile)
    else:
        return audio

