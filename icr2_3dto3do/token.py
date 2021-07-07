# coding: utf-8
class Token(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.attrs = {k.lower() if len(k) == 1 else k: v for k, v in kwargs.items()}

    def __str__(self):
        names = [x.__class__.__name__ for x in self]
        return f'{self.__class__.__name__} {names}'

    def __bool__(self):
        return True


class NIL(Token):  # F00
    pass


class LIST(Token):  # F11
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
