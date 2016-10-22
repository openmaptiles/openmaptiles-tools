from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .tileset import Tileset


def collect_documentation(tileset_filename, layer_filter=None):
    tileset = Tileset.parse(tileset_filename)
    markdown_doc = ''
    for layer in tileset.layers:

        if layer_filter and layer_filter != layer['layer']['id']:
            continue

        markdown_doc += "\n## {layer_id}\n\n{desc}".format(
            layer_id=layer['layer']['id'], desc=layer['layer']['description'])

        fields_doc = ""
        fields = layer['layer'].get('fields', {}).items()
        for field_name, field_desc in fields:
            fields_doc += "- `{name}`: {desc}\n".format(name=field_name, desc=field_desc)
        if len(fields) > 0:
            markdown_doc += "### Fields \n\n{fields}\n".format(fields=fields_doc)

    return markdown_doc
