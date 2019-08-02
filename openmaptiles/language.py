def languages_to_sql(languages):
    name_languages = list(map(lambda l: "NULLIF(tags->'name:" + l + "', '') AS \"name:" + l + "\"", languages))
    name_languages.append("NULLIF(tags->'name_int', '') AS \"name_int\"")
    name_languages.append("NULLIF(tags->'name:latin', '') AS \"name:latin\"")
    name_languages.append("NULLIF(tags->'name:nonlatin', '') AS \"name:nonlatin\"")
    name_languages = ', '.join(name_languages)
    return name_languages
