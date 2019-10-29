def languages_to_sql(languages):
    return ', '.join(languages_as_fields(languages))


def languages_as_fields(languages):
    return [f"NULLIF(tags->'{l}', '') AS \"{l}\"" for l in
            language_codes_to_names(languages)]


def language_codes_to_names(languages):
    return [f"name:{lang}" for lang in languages] + \
           ['name_int', 'name:latin', 'name:nonlatin']
