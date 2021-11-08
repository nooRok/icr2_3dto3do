# coding: utf-8
import re

from .token import *
from .value import Value

_types = {
    'NIL': NIL,
    'LIST': LIST,
    'DATA': DATA,
    'FACE': FACE,
    'BSPF': BSPF,
    'BSPN': BSPN,
    'BSPA': BSPA,
    'FACE2': FACE2,
    'BSP2': BSP2,
    'SWITCH': SWITCH,
    'DYNO': DYNO,
    'POLY': POLY,
    'LINE': LINE,
    'MATERIAL': MATERIAL,
    'DYNAMIC': DYNAMIC,
    'SUPEROBJ': SUPEROBJ,
    'GROUP': GROUP,
    'MIP': MIP,
    'EXTERN': EXTERN,
    'DISTANCE': DISTANCE
}


class ParsingError(Exception):
    pass


class ArgumentsLengthError(ParsingError):
    @classmethod
    def make(cls, msg):
        return cls(f'Invalid arguments length: {msg}')


class FileNameLengthError(ParsingError):
    @classmethod
    def make(cls, msg):
        return cls(f'Invalid filename length (max 8 characters): {msg}')


def clean_text(text: str):  # rem header and comments
    rem_header = re.sub(r'^3D VERSION 3\.0.*', '', text)
    rem_comments = re.sub(r'^\s*%.*', '', rem_header, flags=re.MULTILINE)
    return rem_comments


def split(text: str):  # split text by semicolon at line end
    statements = re.split(r';\s*$', text, flags=re.MULTILINE)
    yield from filter(None, map(str.strip, statements))


def gen_tokens(text: str):
    delimiters = re.compile(r'[\s,]')
    brackets = re.compile(r'[{(\[<>\])}]')
    symbols = re.compile(r'[=]')
    buffer = []
    it_text = iter(text)
    for char in it_text:  # type: str
        if delimiters.match(char) or brackets.match(char) or symbols.match(char):
            if buffer:
                yield ''.join(buffer)
                buffer.clear()
            if delimiters.match(char):
                continue
            yield char
        elif char == '"':
            name = ''.join(iter(it_text.__next__, '"'))
            yield f'"{name}"'
        else:
            buffer.append(char)
    if buffer:
        yield ''.join(buffer)


def get_pair(text: str):
    key, value = re.split(r'\s*:\s*', text, 1)
    return key, [*gen_tokens(value)]


def is_sfn(filename: str):
    return 0 < len(filename.strip('"')) <= 8


def to_attr_pair(t: Token):
    assert len(t) == 1
    return t.name, t[0]


def parse(tokens):  # iterator
    for token in tokens:
        type_ = _types.get(token)
        if type_:
            if type_ == NIL:
                yield type_()
            elif type_ in [POLY, LINE]:
                poly = [*parse(tokens)]
                poly_value = poly.pop()
                poly_attrs = {'t': ['T'] in poly, 'color_name': poly[-1]}
                yield type_(poly_value, **poly_attrs)
            elif type_ in [MATERIAL]:
                mtl = [next(parse(tokens)) for _ in range(2)]  # [GROUP, MIP] or [GROUP|MIP, MATERIAL]
                if isinstance(mtl[-1], (GROUP, MIP)):
                    mtl.append(next(parse(tokens)))
                mtl_value = mtl.pop()
                mtl_attrs = dict(map(to_attr_pair, mtl))
                yield type_([mtl_value], **mtl_attrs)
            elif type_ in [GROUP]:  # MATERIAL sub func
                yield type_([next(parse(tokens))])
            elif type_ in [MIP]:  # MATERIAL sub func
                mip_name = next(parse(tokens))
                if not is_sfn(mip_name):
                    raise FileNameLengthError(f'Invalid MIP filename length (max 8 characters): {mip_name}')
                yield type_([mip_name])
            elif type_ in [DYNAMIC]:
                dyn = [*parse(tokens)]
                if len(dyn) != 8:
                    raise ArgumentsLengthError(f'Invalid DYNAMIC arguments length '
                                               f'({len(dyn)}/8): [{", ".join(map(str, dyn))}]')
                dyn_attrs = dict([to_attr_pair(dyn.pop())])
                yield type_(dyn, **dyn_attrs)
            elif type_ in [EXTERN]:  # DYNAMIC sub func
                ext_name = next(parse(tokens))
                if not is_sfn(ext_name):
                    raise FileNameLengthError(f'Invalid EXTERN filename length (max 8 characters): {ext_name}')
                yield type_([ext_name])
            elif type_ in [SWITCH]:
                dst = next(parse(tokens))  # DISTANCE object
                if not isinstance(dst, DISTANCE):
                    raise ParsingError('A token following SWITCH must be DISTANCE')
                swt_values = [*dst]
                swt_attrs = {'distance': [*dst], **dst.attrs}
                yield type_(swt_values, **swt_attrs)
            elif type_ in [DISTANCE]:  # DISTANCE sub func
                dst_attrs = {'origin': next(parse(tokens))[0], 'symbol': next(tokens)}
                dst_values = next(parse(tokens))
                yield type_(dst_values, **dst_attrs)
            elif type_ in [FACE, BSPA, BSPF, BSPN, FACE2, BSP2]:
                bsp_ = next(parse(tokens))
                if len(bsp_) != 3:
                    raise ArgumentsLengthError(f'Invalid BSP normal arguments length '
                                               f'({len(bsp_)}/3): [{", ".join(bsp_)}]')
                bsp_attr = {'bsp': bsp_}
                bsp_values = []
                try:
                    for _ in range(type_.size):
                        bsp_values.append(next(parse(tokens)))
                except StopIteration:
                    raise ArgumentsLengthError(f'Invalid {type_().name} arguments length '
                                               f'({len(bsp_values)}/{type_.size})')
                yield type_(bsp_values, **bsp_attr)
            elif type_ in [SUPEROBJ]:
                f16_attrs = {'pointer': next(parse(tokens))}
                yield type_(next(parse(tokens)), **f16_attrs)
            elif type_ in [LIST, DYNO, DATA]:
                yield type_(next(parse(tokens)))
        elif token in '<':
            yield [*map(float, parse(tokens))]
        elif token in '[':
            val = [*parse(tokens)]
            value = val.pop(0)
            attrs = {k: v for k, v in zip(val[::2], val[1::2])}
            yield Value(value, **attrs)
        elif token in '({':
            yield [*parse(tokens)]
            if token == '{':
                return
        elif token in '>])}':
            return
        elif token in ',=':
            pass
        else:
            yield token
