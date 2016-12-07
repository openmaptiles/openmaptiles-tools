from collections import namedtuple

from graphviz import Digraph

Table = namedtuple('Table', ['name', 'fields', 'mapping', 'type'])


def values_label(osm_values):
    return '\n'.join(osm_values)


def normalize_graphviz_labels(label):
    return label.replace(':', '_')


def generate_mapping_subgraph(table):
    subgraph = Digraph(table.name, node_attr={
        'width:': '20',
        'fixed_size': 'shape'
    })

    subgraph.node(table.name, shape='box')

    for osm_key, osm_values in table.mapping:
        node_name = 'key_' + normalize_graphviz_labels(osm_key)
        subgraph.node(node_name, label=osm_key, shape='box')

        subgraph.edge(node_name, table.name,
                      label=values_label(osm_values))

    return subgraph


def replace_generalization_postfix(table_name):
    return table_name.replace('_gen0', '').replace('_gen1', '')


def merge_grouped_mappings(mappings):
    """Merge multiple mappings into a single mapping for drawing"""
    for mapping_group, mapping_value in mappings.items():
        yield mapping_group, mapping_value['mapping']


def find_tables(config):
    for table_name, table_value in config['tables'].items():
        fields = table_value.get('fields')

        if table_value.get('mappings'):
            mapping = list(merge_grouped_mappings(table_value['mappings']))
        else:
            mapping = table_value.get('mapping', {}).items()

        if mapping and fields:
            yield Table(table_name, fields, mapping, table_value['type'])


def generate_table_mapping_diagram(mapping_config):
    graph = Digraph('Imposm Mapping', format='png', graph_attr={
        'rankdir': 'LR',
        'ranksep': '3'
    })

    for table in find_tables(mapping_config):
        graph.subgraph(generate_mapping_subgraph(table))

    return graph
