from typing import Iterable

# These codes will always be included, in addition to the ones in tile definition
default_language_codes = ['name_int', 'name:latin', 'name:nonlatin']


def languages_to_sql(language_codes):
    """Creates a complete SQL comma-separated expression of language fields"""
    return ', '.join(languages_as_fields(language_codes))


def languages_as_fields(language_codes):
    """Converts language codes into a list of SQL fields:
        en   =>   NULLIF(tags->'name:en', '') AS name:en
    """
    return [f"NULLIF(tags->'{l}', '') AS \"{l}\"" for l in
            language_codes_to_names(language_codes)]


def language_codes_to_names(language_codes: Iterable[str]):
    """
    Given a list of language codes, returns a list of SQL field names,
    decorated as "name:code", as well as the default ones.
    """
    return [f"name:{lang}" for lang in language_codes] + default_language_codes
