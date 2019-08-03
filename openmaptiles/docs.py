def generate_field_doc(field_name, field_spec):
    field_doc = f"### {field_name.strip()}\n"

    if isinstance(field_spec, dict):
        desc = field_spec.get('description', '')
        field_doc += "\n" + desc.strip() + "\n"

        values = field_spec.get('values', [])
        if len(values) > 0:
            field_doc += "\nPossible values:\n\n"
            for value in values:
                field_doc += f"- `{value}`\n"
            field_doc += "\n"
    else:
        field_doc += "\n" + field_spec.strip() + "\n\n"

    return field_doc


def collect_documentation(layer):
    markdown_doc = layer['layer'].get('description', '').strip()
    markdown_doc += 2 * "\n"

    fields_doc = ""
    fields = layer['layer'].get('fields', {}).items()
    for field_name, field_spec in fields:
        fields_doc += generate_field_doc(field_name, field_spec)

    if len(fields) > 0:
        markdown_doc += f"## Fields\n\n{fields_doc}\n"

    markdown_doc += "\n"
    return markdown_doc
