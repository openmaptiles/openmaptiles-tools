from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .tileset import Layer
import os.path


def collect_documentation(layer, diagram=None):
    markdown_doc = "# {layer_id}\n\n{desc}\n\n".format(
        layer_id=layer['layer']['id'].strip(),
        desc=layer['layer'].get('description', '').strip()
    )

    fields_doc = ""
    fields = layer['layer'].get('fields', {}).items()
    for field_name, field_desc in fields:
        fields_doc += "- **{name}**: {desc}\n".format(
            name=field_name.strip(),
            desc=field_desc.strip()
        )
    if len(fields) > 0:
        markdown_doc += "## Fields\n\n{fields}\n".format(fields=fields_doc)

    if diagram:
        markdown_doc += "## Mapping\n\n![]({diagram_file}.png)\n".format(diagram_file=os.path.basename(diagram))


    markdown_doc += "\n"
    return markdown_doc
