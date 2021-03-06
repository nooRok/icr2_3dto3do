# coding: utf-8
class Token(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.attrs = {k.lower() if len(k) == 1 else k: v for k, v in kwargs.items()}

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        return f'({self.name}: {{{", ".join(map(str, self))}}})'

    def __bool__(self):
        return True


class NIL(Token):  # F00
    pass


class LIST(Token):  # F11
    pass


class SUPEROBJ(Token):
    pass


class LINE(Token):  # NIL
    pass


class POLY(LINE):  # F01/F02
    pass


class BspToken(Token):
    size = None
    type = None


class FACE(BspToken):
    size = 1
    type = 5


class BSPF(BspToken):
    size = 3
    type = 7


class BSPN(BspToken):
    size = 2
    type = 10


class BSPA(BspToken):
    size = 3
    type = 8


class FACE2(BspToken):
    size = 2
    type = 6


class BSP2(BspToken):
    size = 4
    type = 9


class MATERIAL(Token):  # F04/F02
    pass


class SWITCH(Token):  # F13
    pass


class DYNO(Token):  # F12
    pass


class DATA(Token):  # F17/track hash
    pass


class DYNAMIC(Token):  # F15
    pass


class DISTANCE(Token):  # F13 values
    pass


class GROUP(Token):  # F02 texture type
    pass


class MIP(Token):  # F04 filename
    pass


class EXTERN(Token):  # F15 filename
    pass
