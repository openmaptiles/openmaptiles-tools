import json
from pathlib import Path
from openmaptiles.tileset import Tileset


def fp_to_dict(fp: Path) -> dict:
    return json.loads(fp.read_text(encoding="utf-8"))


def get_ts_lyr_style_json_fp(yaml_fp: str) -> Path:
    yaml_path = yaml_fp.filename
    json_name = Path(yaml_path.name).with_suffix('.json')
    ts_lyr_dir = yaml_path.parent

    return ts_lyr_dir.joinpath(json_name)


def add_order(lyrs: list) -> list:
    for i, lyr in enumerate(lyrs):
        lyr['order'] = i
    return lyrs


def get_order(layer: dict) -> int:
    order = layer.get('order')
    if order is None:
        raise ValueError(f"Missing order value in layer {layer.get('id')}")
    return int(order)


def split(tileset_fp: Path, style_fp: Path):
    tileset = Tileset.parse(tileset_fp)
    tileset_lyrs = tileset.layers

    # Add order to each style layer (e.g. backgroud - 0, labels - 196)
    style = fp_to_dict(style_fp)
    lyrs = style.get('layers')
    if not lyrs:
        raise ValueError(f"No layers in {style_fp}.")
    style_lyrs_w_order = add_order(lyrs)

    # ts_lyr is a layer in tileset.yaml (e.g. landuse, landcover, water, waterway...)
    for ts_lyr in tileset_lyrs:
        snippet_fp = get_ts_lyr_style_json_fp(ts_lyr)
        snippet_lyrs = list()
        for style_lyr in style_lyrs_w_order:
            source_layer = style_lyr.get('source-layer')
            if source_layer == ts_lyr.filename.stem:
                snippet_lyrs.append(style_lyr)
        out_dict = {'layers': snippet_lyrs}

        # write style layers with order to json for specific tileset layer
        snippet_fp.write_text(json.dumps(out_dict, indent=2))


def merge(tileset_fp: Path, style_fp: Path, style_header_fp: Path):
    tileset = Tileset.parse(tileset_fp)
    tileset_lyrs = tileset.layers
    # Load style header file
    style = fp_to_dict(style_header_fp)

    style_lyrs = list()
    # For each tileset layer read its style.json and append its layers to style_lyrs
    for ts_lyr in tileset_lyrs:
        ts_lyr_style_json_fp = get_ts_lyr_style_json_fp(ts_lyr)
        with open(ts_lyr_style_json_fp, 'r') as f:
            in_dict = json.load(f)
        ts_lyr_style_lyrs = in_dict.get('layers')
        for layer_style_layer in ts_lyr_style_lyrs:
            if layer_style_layer.get('order') is None:
                raise ValueError(f'Missing order value in layer {layer_style_layer.get("id")} '
                                 f'of snippet {ts_lyr_style_json_fp}.')
            else:
                style_lyrs.append(layer_style_layer)

    # sort style_lyrs by order, let sort take care of duplicates
    style_lyrs.sort(key=get_order)
    # create a new list with original background layer
    new_style_lyrs = style.get('layers')[:1]
    # append sorted layers to new_style_lyrs
    for style_lyr in style_lyrs:
        # remove order kv
        style_lyr.pop('order')
        new_style_lyrs.append(style_lyr)
    style['layers'] = new_style_lyrs
    # save to temp file
    with open(style_fp, 'w') as fout:
        json.dump(style, fout, indent=2)
