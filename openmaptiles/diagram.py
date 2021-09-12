import re
from pathlib import Path

from graphviz import Digraph
from typing import Tuple, List

from openmaptiles.tileset import process_layers, Layer


class GraphGenerator:
    def __init__(self, filename, layerId, output_dir, compare_dir, cleanup, extensions):
        self.messages = []
        self.filename = Path(filename)
        self.layerId = layerId
        self.output_dir = Path(output_dir)
        self.compare_dir = Path(compare_dir) if compare_dir else None
        self.cleanup = cleanup
        self.extensions = extensions

    def do_layer(self, layer, is_tileset) -> None:
        graph, path = self.get_graph(layer, is_tileset)
        path.parent.mkdir(parents=True, exist_ok=True)
        for ext in self.extensions:
            print(f"{'Verifying' if self.compare_dir else 'Creating'} {path}.{ext}")
            new_file = graph.render(filename=path, format=ext, cleanup=self.cleanup)
            self.compare_file(path, '.' + ext, new_file)
        if not self.cleanup:
            self.compare_file(path, '', path)

    def get_graph(self, layer: Layer, is_tileset: bool) -> Tuple[Digraph, Path]:
        pass

    def compare_file(self, dot_file, ext, new_file):
        if not self.compare_dir:
            return
        cmp_with = Path(self.compare_dir,
                        dot_file.relative_to(self.output_dir)).with_suffix(ext)
        try:
            old = cmp_with.read_bytes()
            new = Path(new_file).read_bytes()
            if old != new:
                raise ValueError(f'file has changed, old size = '
                                 f'{len(old):,} B,  new = {len(new):,} B')
        except Exception as ex:
            self.messages.append(f"Error validating {cmp_with}: {ex}")

    def run(self) -> int:
        process_layers(self.filename, self.do_layer, self.layerId)
        if self.messages:
            print(f'Validation errors:')
            for msg in self.messages:
                print(msg)
            return 1
        return 0


class EtlGraph(GraphGenerator):
    # search for  '# etldoc:...' and '-- etldoc:...'
    re_mapping = re.compile(r'^\s*#\s*etldoc\s*:(.*)$')
    re_schema = re.compile(r'^\s*--\s*etldoc\s*:(.*)$')

    def get_graph(self, layer: Layer, is_tileset: bool) -> Tuple[Digraph, Path]:
        raw_lines = self.parse_files(layer.imposm_mapping_files, self.re_mapping) + \
                    self.parse_files(layer.schemas, self.re_schema)
        # Combine etldoc lines that are broken up into multiple:
        # if a line has unclosed "[", concatenate it with subsequent ones until closed
        lines = []
        count = 0
        for line in raw_lines:
            open_count = line.count('[')
            close_count = line.count(']')
            if count == 0:
                lines.append(line)
            else:
                lines[-1] += ' ' + line
            count += open_count - close_count
        if count != 0:
            raise ValueError(f"Etldoc in layer {layer.id} has unmatched '[' and ']'")
        # Remove duplicates preserving order
        lines = list(dict.fromkeys(lines))
        if is_tileset:
            path = self.output_dir / layer.id / 'etl_diagram'
        else:
            path = self.output_dir / f'etl_{layer.id}'
        return Digraph('G', graph_attr=dict(rankdir='LR'), body=lines), path

    @staticmethod
    def parse_files(content_list: list, matcher: re) -> List[str]:
        result = []
        for item in content_list:
            content = item.read_text('utf-8') if isinstance(item, Path) else item
            for line in content.splitlines():
                m = matcher.match(line)
                if m:
                    value = m.group(1).strip(' \t\n\r')
                    # replace multiple consequent space/tabs with a single space
                    value = re.sub(r'\s+', ' ', value)
                    result.append(value)
        return result


class MappingGraph(GraphGenerator):
    def get_graph(self, layer: Layer, is_tileset: bool) -> Tuple[Digraph, Path]:
        graph = Digraph('Imposm Mapping', graph_attr=dict(rankdir='LR', ranksep='3'))

        for imposm_mapping in layer.imposm_mappings:
            for name, value in imposm_mapping['tables'].items():
                mapping = value.get('type_mappings') or value.get('mapping')
                if mapping:
                    graph.subgraph(
                        self.generate_mapping_subgraph(name, mapping.items()))

        path = self.output_dir
        if is_tileset:
            path = path / layer.id / 'mapping_diagram'
        return graph, path

    @staticmethod
    def generate_mapping_subgraph(name, mapping):
        subgraph = Digraph(name, node_attr=dict(fixed_size='shape'))
        subgraph.node(name, shape='box')
        for osm_key, osm_values in mapping:
            node_name = 'key_' + osm_key.replace(':', '_')
            subgraph.node(node_name, label=osm_key, shape='box')
            subgraph.edge(node_name, name, label='\n'.join(osm_values))

        return subgraph
