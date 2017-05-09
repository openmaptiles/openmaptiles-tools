import re


def languages_to_sql(languages):
    name_languages = list(map(lambda l: "NULLIF(tags->'name:"+l+"', '') AS \"name:"+l+"\"", languages))
    name_languages.append("COALESCE(NULLIF(tags->'int_name', ''), tags->'name')");
    name_languages = ', '.join(name_languages)
    return name_languages
