# coding: utf-8
from icr2model.flavor import build_flavor
from icr2model.flavor.flavor import VertexFlavor, F17
from icr2model.flavor.value.unit import to_papy_angle
from icr2model.flavor.value.values import BspValues
from . import parser
from .token import *
from .value import Value

_texture_flags = {0: 1,  # asphalt
                  1: 2,  # grass
                  2: 4,  # wall
                  3: 8}  # tso


class DuplicatedDefinitionError(Exception):
    pass


class Converter:
    lod_divisor = 2

    def __init__(self, definitions):
        self.definitions = definitions  # dict from .3d file
        self.track_hash = ''
        self.scaling_factor = 1.0
        self.flavors = {0: build_flavor(0, 0)}
        self.mips = {}
        self.pmps = {}  # NotImplemented
        self.f15s = {}
        self.offsets = {}  # def name: offset

    def is_track(self):
        return bool(self.track_hash)

    def store_flavor(self, type_: int, values1=None, values2=None):
        offset = max(self.flavors) + 1
        flavor = build_flavor(type_, offset, values1=values1, values2=values2)
        self.flavors[offset] = flavor
        return offset

    def _store_vertex_flavor(self, v1, v2=None):
        assert isinstance(v1, Value)
        return self.store_flavor(0, v1 * self.scaling_factor, v2 or [])

    def _get_value(self, key):
        if isinstance(key, str):
            return self.definitions[key]
        return key

    def _build_flavor(self, def_, **attrs):
        if isinstance(def_, str):
            if def_ in self.offsets:
                return self.offsets[def_]
            offset = self._build_flavor(self.definitions[def_], **attrs)
            self.offsets[def_] = offset
            return offset
        attrs_ = {**attrs, **def_.attrs}
        if isinstance(def_, NIL):
            return 0
        elif isinstance(def_, POLY):
            vertices = (self._get_value(v) for v in def_)
            vtx_v2 = [self._store_vertex_flavor(vtx, vtx.attrs.get('t')) for vtx in vertices]
            color_name = def_.attrs['color_name']
            color_idx = self._get_value(color_name)
            vtx_v1 = [color_idx if isinstance(color_idx, (int, float)) else color_idx[0], len(vtx_v2) - 1]
            type_ = 2 if def_.attrs.get('t') else 1
            if type_ == 2:
                # name = attrs['MIP']  # from MATERIAL MIP = "xxx"
                group = int(attrs_.get('GROUP', 8))  # from MATERIAL GROUP = n
                tex_flag = _texture_flags.get(group, group)  # default: 8(tso)
                vtx_v1 = [tex_flag] + vtx_v1
            return self.store_flavor(type_, vtx_v1, vtx_v2)
        elif isinstance(def_, LINE):
            return 0  # NIL
        elif isinstance(def_, SWITCH):
            origin = def_.attrs['origin']
            origin_o = self._store_vertex_flavor(self._get_value(origin))
            dd_pairs = [(int(v[0]), v[2]) for v in def_]  # [(distance, def/def_name), ...]
            do_pairs = [(int(d * self.scaling_factor), self._build_flavor(o, **attrs_))
                        for d, o in dd_pairs]  # [(distance, offset), ...]
            f13_v2 = [value for pair in do_pairs for value in pair]  # flatten pairs
            return self.store_flavor(13, [origin_o], f13_v2)
        elif isinstance(def_, MATERIAL):
            f04_v2 = [self._build_flavor(c, **attrs_) for c in def_]
            assert len(f04_v2) == 1
            if def_.attrs.get('MIP'):
                mip_name = def_.attrs['MIP']  # .strip('"')
                mip_index = self.mips.setdefault(mip_name, len(self.mips))
                return self.store_flavor(4, [mip_index, 0], f04_v2)
            else:
                return f04_v2[0]
        elif isinstance(def_, (FACE, BSPA, BSPN, BSPF, FACE2, BSP2)):
            if self.is_track() and isinstance(def_, FACE):
                return self._build_flavor(def_[0], **attrs_)
            bsp_attr = [self._get_value(v) for v in def_.attrs['bsp']]
            bsp_coords = [val * self.scaling_factor for val in bsp_attr]
            bsp_v1 = BspValues.from_coordinates(*bsp_coords)
            bsp_v2 = [self._build_flavor(c, **attrs_) for c in def_]
            bsp_v2 = [bsp_v2[0]] + bsp_v2[1:][::-1]
            return self.store_flavor(def_.type, bsp_v1, bsp_v2)  # [v2[0]] + v2[1:][::-1])
        elif isinstance(def_, LIST):
            if self.is_track() and self.track_hash in self.definitions and self.track_hash in def_:
                assert def_[0] == self.track_hash
                f11offsets = [self._build_flavor(v, **attrs_) for v in def_[1:]]
                f11fs = [self.flavors.pop(f11o_) for f11o_ in f11offsets]
                assert all(len(f.values2) == 8 for f in f11fs)  # 8: [4 HI] + [2 MED] + [1 LO] + [F17 offset]
                f17fs = [self.flavors.pop(f11f.values2.pop()) for f11f in f11fs]
                assert all(isinstance(f, F17) for f in f17fs)
                pairs = [p for p in zip(f11fs, f17fs)]
                f11os = []  # LOD F11s
                ex_len = len(pairs) // self.lod_divisor
                for f11, f17 in pairs[-ex_len:] + pairs + pairs[:ex_len]:
                    f11o = self.store_flavor(11, [7], f11.values2)
                    f17o = self.store_flavor(17, f17.values1)
                    self.flavors[f17o].parents.append(f11o)
                    f11os.append(f11o)
                root_f11o = self.store_flavor(11, [len(f11os)], f11os)  # parent of LOD F11s
                hash_os = f11os[ex_len:]
                hash_def = map(int, self.definitions.pop(self.track_hash))
                hash_v2 = [root_f11o] + [hash_os[i] for i in hash_def]
                return self.store_flavor(11, [len(hash_v2)], hash_v2)
            f11_v2 = [self._build_flavor(x, **attrs_) for x in def_]
            return self.store_flavor(11, [len(f11_v2)], f11_v2)
        elif isinstance(def_, SUPEROBJ):
            f16_ptr = def_.attrs['pointer']
            f16_v1 = [self._build_flavor(f16_ptr, **attrs_)]
            f16_v2 = [self._build_flavor(c, **attrs_) for c in def_]
            return self.store_flavor(16, f16_v1 + [len(f16_v2)], f16_v2)
        elif isinstance(def_, DYNO):
            return self.store_flavor(12, map(int, def_))
        elif isinstance(def_, DATA):
            return self.store_flavor(17, map(int, def_))
        elif isinstance(def_, DYNAMIC):
            f15_name = def_.attrs['EXTERN']  # .strip('"')
            f15_index = self.f15s.setdefault(f15_name, len(self.f15s))
            f15values = [*map(int, def_[:6])]
            loc = Value(f15values[:3]) * self.scaling_factor
            rot = [to_papy_angle(x / 10.0) for x in f15values[3:7]]
            f15_v1 = loc + rot + [~f15_index]
            flavor = self.store_flavor(15, f15_v1)
            return flavor
        else:
            raise NotImplementedError(def_)

    def build_flavors(self, root: str, scaling_factor=1.0, *, track_hash=''):
        self.track_hash = track_hash
        self.scaling_factor = scaling_factor
        self._build_flavor(self.definitions[root])
        return self.flavors

    def get_files(self):
        return {'mip': [n.strip('"') for n, _ in sorted(self.mips.items(), key=lambda x: x[1])],
                'pmp': [n.strip('"') for n, _ in sorted(self.pmps.items(), key=lambda x: x[1])],
                '3do': [n.strip('"') for n, _ in sorted(self.f15s.items(), key=lambda x: x[1])]}

    @classmethod
    def read_3d(cls, text: str, allow_duplicate=False):
        text_ = parser.clean_text(text)
        pairs = [parser.get_pair(s) for s in parser.split(text_)]
        definitions = {}
        for k, v in pairs:
            if k in definitions and not allow_duplicate:
                raise DuplicatedDefinitionError(f'"{k}" is already defined')
            try:
                definitions[k] = next(parser.parse(iter(v)))
            except parser.ParsingError as e:
                raise parser.ParsingError(f'({k}) {e}')
        color_items = [(k, v) for k, v in definitions.items()
                       if isinstance(v, Value) and v.attrs.get('c')]
        colors = {f'{k}.c': v.attrs['c'][0] for k, v in color_items}
        for c in colors:
            assert c not in definitions
        definitions.update(colors)
        return cls(definitions)

    @classmethod
    def open_3d(cls, path: str, allow_duplicate=False):
        with open(path) as f:
            text = f.read()
        return cls.read_3d(text, allow_duplicate)
