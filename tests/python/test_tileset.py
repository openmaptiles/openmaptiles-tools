import warnings
from unittest import main, TestCase
from typing import Optional
from tests.python.test_helpers import Case, parsed_data

from openmaptiles.tileset import Tileset


class TilesetTestCase(TestCase):
    def _ts_overrides(self,
                      layer: Optional[dict] = None,
                      override_ts: Optional[dict] = None,
                      override_layer: Optional[dict] = None,
                      env: Optional[dict] = None):
        data = parsed_data([Case('my_id', 'my_query;')])

        ts_data = data.data['tileset']
        if override_ts is not None:
            ts_data['overrides'] = override_ts
        if layer is not None:
            ts_data['layers'][0]['file'].data['layer'].update(layer)
        if override_layer is not None:
            ts_data['layers'][0].update(override_layer)

        return Tileset(data, getenv=env.get if env else None)

    def _assert_layer(self, expected_layer: dict,
                      layer: Optional[dict] = None,
                      override_ts: Optional[dict] = None,
                      override_layer: Optional[dict] = None,
                      env: Optional[dict] = None):
        ts = self._ts_overrides(layer, override_ts, override_layer, env)

        for k in expected_layer.keys():
            self.assertEqual(getattr(ts.layers_by_id['my_id'], k), expected_layer[k])

    def test_overrides(self):
        buf_0 = dict(buffer_size=0)
        buf_1 = dict(buffer_size=1)
        buf_2 = dict(buffer_size=2)
        buf_3 = dict(buffer_size=3)
        min_1 = dict(min_buffer_size=1)
        min_2 = dict(min_buffer_size=2)
        min_3 = dict(min_buffer_size=3)

        self._assert_layer(buf_2, buf_2)
        self._assert_layer(buf_0, buf_2, override_ts=buf_0)
        self._assert_layer(buf_1, buf_2, override_ts=buf_1)
        self._assert_layer(buf_3, buf_2, override_ts=buf_3)
        self._assert_layer(buf_1, min_1 | buf_2, override_ts=buf_0)
        self._assert_layer(buf_1, buf_2, override_layer=buf_1)
        self._assert_layer(buf_2, min_2 | buf_3, override_layer=buf_1)
        self._assert_layer(buf_3, min_1 | buf_2, override_layer=min_3)
        self._assert_layer(buf_3, min_1 | buf_2, override_layer=min_2 | buf_3, override_ts=buf_0)

        env_0 = dict(TILE_BUFFER_SIZE='0')
        env_2 = dict(TILE_BUFFER_SIZE='2')
        self._assert_layer(buf_2, min_1 | buf_2, override_layer=min_2 | buf_3, override_ts=buf_0, env=env_0)
        self._assert_layer(buf_2, buf_1, env=env_2)
        self._assert_layer(buf_2, min_2 | buf_3, env=env_0)
        self._assert_layer(buf_2, min_1 | buf_3, override_ts=buf_0, env=env_2)
        self._assert_layer(buf_2, buf_2, dict(TILE_BUFFER_SIZE=''))

        # str parsing
        self._assert_layer(dict(buffer_size=2), dict(buffer_size='2'))

    def _ts_parse(self, reqs, expected_layers, expected_tables, expected_funcs, extra_cases=None):
        cases = [] if not extra_cases else list(extra_cases)
        cases.append(Case('my_id', 'my_query;', reqs=reqs))
        ts = Tileset(parsed_data(cases))
        self.assertEqual(ts.attribution, 'test_attribution')
        self.assertEqual(ts.bounds, 'test_bounds')
        self.assertEqual(ts.center, 'test_center')
        self.assertEqual(ts.defaults, dict(srs='test_srs', datasource=dict(srid='test_datasource')))
        self.assertEqual(ts.id, 'id1')
        self.assertEqual(ts.maxzoom, 'test_maxzoom')
        self.assertEqual(ts.minzoom, 'test_minzoom')
        self.assertEqual(ts.name, 'test_name')
        self.assertEqual(ts.pixel_scale, 'test_pixel_scale')
        self.assertEqual(ts.version, 'test_version')

        self.assertEqual(len(ts.layers), len(cases))
        layer = ts.layers_by_id['my_id']
        self.assertEqual(layer.id, 'my_id')
        self.assertEqual(layer.requires_layers, expected_layers)
        self.assertEqual(layer.requires_tables, expected_tables)
        self.assertEqual(layer.requires_functions, expected_funcs)
        self.assertEqual(layer.buffer_size, 10)

        # This test can be deleted once we remove the deprecated property in some future version
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            self.assertEqual(layer.requires, expected_layers)

    def test_ts_parse(self):
        extra = [Case('c1', 'SELECT 1;')]

        self._ts_parse(None, [], [], [])
        self._ts_parse([], [], [], [])
        self._ts_parse({}, [], [], [])
        self._ts_parse('c1', ['c1'], [], [], extra)
        self._ts_parse(['c1'], ['c1'], [], [], extra)
        self._ts_parse(dict(layers='c1'), ['c1'], [], [], extra)
        self._ts_parse(dict(layers=['c1']), ['c1'], [], [], extra)
        self._ts_parse(dict(tables='a'), [], ['a'], [])
        self._ts_parse(dict(tables=['a', 'b']), [], ['a', 'b'], [])
        self._ts_parse(dict(functions='x'), [], [], ['x'])
        self._ts_parse(dict(functions=['x', 'y']), [], [], ['x', 'y'])
        self._ts_parse(dict(layers=['c1'], tables=['a', 'b'], functions=['x', 'y']),
                       ['c1'], ['a', 'b'], ['x', 'y'], extra)

    def _assert_layer_vars(self, expected_vars: dict,
                           layer: Optional[dict] = None,
                           override_ts: Optional[dict] = None,
                           override_layer: Optional[dict] = None,
                           env: Optional[dict] = None):
        ts = self._ts_overrides(layer, override_ts, override_layer, env)

        for k in expected_vars.keys():
            self.assertEqual(ts.layers_by_id['my_id'].vars.get(k), expected_vars[k])

    def test_layer_var(self):
        data = parsed_data([Case('my_id', 'my_query;')])
        ts = Tileset(data)
        self.assertEqual(ts.layers_by_id['my_id'].vars, {})
        self._assert_layer_vars(dict(custom_zoom=None))
        self._assert_layer_vars(dict(custom_zoom=14),
                                dict(vars=dict(custom_zoom=14)))
        self._assert_layer_vars(dict(custom_zoom=12),
                                dict(vars=dict(custom_zoom=14)),
                                override_layer=dict(vars=dict(custom_zoom=12)))
        self._assert_layer_vars(dict(custom_zoom=12),
                                dict(vars=dict(custom_zoom=14)),
                                override_ts=dict(vars=dict(custom_zoom=12)))
        self._assert_layer_vars(dict(custom_zoom=None),
                                dict(),
                                override_ts=dict(vars=dict(custom_zoom=12)))
        self._assert_layer_vars(dict(custom_zoom=13),
                                dict(vars=dict(custom_zoom=14)),
                                override_layer=dict(vars=dict(custom_zoom=13)),
                                override_ts=dict(vars=dict(custom_zoom=12)))
        self.assertRaises(ValueError, self._assert_layer_vars,
                          dict(custom_zoom=14),
                          dict(vars=dict(custom_zoom=14)),
                          override_layer=dict(vars=dict(custom_zoom2=12)))

        env = dict(OMT_VAR_custom_zoom=12)
        self._assert_layer_vars(dict(custom_zoom=12),
                                dict(vars=dict(custom_zoom=13)),
                                env=env)


if __name__ == '__main__':
    main()
