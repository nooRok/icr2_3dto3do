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
    'SUPEROBJ': SUPEROBJ
}


class ParsingError(Exception):
    pass


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


def parse(tokens):  # iterator
    for token in tokens:
        type_ = _types.get(token)
        if type_:
            if type_ == NIL:
                yield type_()
            elif type_ in [POLY, LINE]:
                poly = [*parse(tokens)]
                attrs_ = poly[:-1]
                poly_attrs = {'t': ['T'] in attrs_, 'color_name': attrs_[-1]}
                yield type_(poly[-1], **poly_attrs)
            elif type_ in [MATERIAL]:
                mtl_attrs = {}
                while True:
                    next_ = next(parse(tokens))
                    if next_ in ['GROUP', 'MIP']:  # MATERIAL attrs
                        mtl_attrs[next_] = next(parse(tokens))
                    else:
                        break
                yield type_([next_], **mtl_attrs)
            elif type_ in [DYNAMIC]:
                dyn = [*parse(tokens)]  # or range(9)
                assert len(dyn) == 9
                dyn_attrs = {dyn[-2]: dyn[-1]}
                yield type_(dyn[:7], **dyn_attrs)
            elif type_ in [SWITCH]:
                assert next(tokens) == 'DISTANCE'
                swt_attrs = {'origin': next(parse(tokens))[0], 'symbol': next(tokens)}
                swt_values = next(parse(tokens))
                yield type_(swt_values, **swt_attrs)
            elif type_ in [FACE, BSPA, BSPF, BSPN, FACE2, BSP2]:
                bsp_ = next(parse(tokens))
                assert len(bsp_) == 3
                bsp_attr = {'bsp': bsp_}
                bsp_values = [next(parse(tokens)) for _ in range(type_.size)]
                yield type_(bsp_values, **bsp_attr)
            elif type_ in [SUPEROBJ]:
                f16_attrs = {'pointer': next(parse(tokens))}
                yield type_(next(parse(tokens)), **f16_attrs)
            elif type_ in [LIST]:
                yield type_(next(parse(tokens)))
            elif type_ in [DYNO]:
                yield type_(next(parse(tokens)))
            elif type_ in [DATA]:
                yield type_(next(parse(tokens)))
        elif token in '<':
            yield [*map(int, parse(tokens))]
        elif token in '[':
            values = [*parse(tokens)]
            pairs = zip(values[1:][::2], values[1:][1::2])
            attrs = {k: v for k, v in pairs}
            yield Value(values[0], **attrs)
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
