from typing import List, Union, Dict
from dataclasses import dataclass
from pathlib import Path

from openmaptiles.tileset import ParsedData


@dataclass
class Case:
    id: str
    query: str
    reqs: Union[str, List[str], Dict[str, Union[str, List[str]]]] = None


def parsed_data(layers: Union[Case, List[Case]]):
    return ParsedData(dict(
        tileset=(dict(
            attribution='test_attribution',
            bounds='test_bounds',
            center='test_center',
            defaults=dict(srs='test_srs', datasource=dict(srid='test_datasource')),
            id='id1',
            layers=[
                dict(file=ParsedData(dict(
                    layer=dict(
                        buffer_size='10',
                        datasource=dict(query='test_query'),
                        id=v.id,
                        fields={},
                        requires=[v.reqs] if isinstance(v.reqs, str) else v.reqs or []
                    ),
                    schema=[ParsedData(v.query, Path(v.id + '_s.yaml'))] if v.query else [],
                ), Path(f'./{v.id}.yaml'))) for v in ([layers] if isinstance(layers, Case) else layers)
            ],
            maxzoom='test_maxzoom',
            minzoom='test_minzoom',
            name='test_name',
            pixel_scale='test_pixel_scale',
            version='test_version',
        ))), Path('./tileset.yaml'))
