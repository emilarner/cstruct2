class switch_type:
    def __init__(self, dependent: str, decision_paths: dict, name: str = None):
        self.name = name
        self.dependent = dependent
        self.decisions = decision_paths
        self.wrapper = None

switch = switch_type

class cstruct2_number_field:
    def __init__(self, name: str, width: int, kind: str,
                endianness):

        self.name = name
        self.kind = kind
        self.width = width
        self.endianness = endianness
        self.wrapper = None

class cstruct2_int_field(cstruct2_number_field):
    def __init__(self, name: str, width: int | str, endianness):
        super().__init__(name, width, "int", endianness)

class cstruct2_float_field(cstruct2_number_field):
    def __init__(self, name: str, width: int | str, endianness):
        super(name, width, "float", endianness)

class cstruct2_bytes_field:
    def __init__(self, name: str, width: int | str):
        self.name = name
        self.width = width
        self.wrapper = None

class cstruct2_bits_field:
    def __init__(self, name: str, width: int | str):
        self.name = name
        self.width = width
        self.wrapper = None

class cstruct2_string_field:
    def __init__(self, name: str, width: int | str | None, null: bool = False):
        self.name = name
        
        self.width = width
        self.null = null

        self.wrapper = None
        self.encoding: str = "ascii"

class cstruct2_recursive_wrapper:
    def __init__(self, name: str, another_cstruct):
        self.name = name
        self.another = another_cstruct
        self.wrapper = None
        #self.width = len(another_cstruct)