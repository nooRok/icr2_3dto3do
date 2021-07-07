# coding: utf-8
class Value(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.attrs = {k.lower() if len(k) == 1 else k: v for k, v in kwargs.items()}
