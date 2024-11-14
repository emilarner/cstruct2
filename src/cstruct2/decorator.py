from io import RawIOBase
from typing import NewType, Type
from enum import Enum
from io import BytesIO

from .cstruct2_exceptions import *
from .cstruct2_fields import *
from .cstruct2_utils import *

import math
import sys
import struct

double = float


class Structure:
    def metafield_to_field(
        self, name: str | None, datatype, data: int | str | tuple, anonymous=False
    ):
        """
        Given a metafield value, parse it into a field, then add it to our store.
        Kinda an internal function: use carefully.
        """

        # No name in the structured class definition can have a leading unscore,
        # because whatever.
        if isinstance(name, str):
            if name.startswith("_"):
                raise cstruct2_field_exception(
                    f"Having a field, {name}, prefixed with an underscore _ is illegal."
                )

            if name in ["null", "pascal", "pascal16"]:
                raise cstruct2_field_exception(
                    "A field cannot be named 'null', 'pascal', or 'pascal16'."
                )

        value = data
        wrapper = lambda x: x
        field = None
        width: int | str = None

        # Determine the wrapper argument when data is given as a tuple.
        if isinstance(data, tuple):
            if isinstance(field, cstruct2_recursive_wrapper):
                wrapper = data[1]

            else:
                if len(data) >= 3:
                    wrapper = data[2]

        # Sure, Python has a switch-like control flow structure now, but it wouldn't really
        # fit the way we parse the annotations. We're committing sins of using strings as
        # enumerated values, but only because Python forced our hand in the first place.
        # If one wanted to get really fancy, one could generate a perfect hash table to all of
        # the type annotations we're forced to process. It would be faster, but at what cost?

        if isinstance(data, list):
            # Is the field data provided by the list in scalar or tuple format?
            field_data = data[1] if len(data) == 2 else tuple(data[1:])

            parsed_field = self.metafield_to_field(name, datatype, field_data, True)
            field = [name, data[0], parsed_field]
            width = data[0]

        elif datatype == "int":
            endianness = "little"  # default endianness is always Little Endian
            width = data

            if isinstance(data, tuple):
                width = data[1]
                endianness = data[0]

            if isinstance(width, int):
                if width not in [1, 2, 4, 8]:
                    raise AttributeError(
                        "An int datatype cannot have an explicit width not 1, 2, 4, or 8 bytes."
                    )

            endianness = relative_endianness_resolver(endianness)

            field = cstruct2_int_field(name, width, endianness)

            field.wrapper = wrapper

        elif datatype == "float":
            width = data
            endianness = "little"  # default endianness is always little endian

            if isinstance(data, tuple):
                width = data[1]
                endianness = data[0]

            if isinstance(width, int):
                if width not in [4, 8]:
                    raise AttributeError(
                        "A float datatype cannot have an explicit width not 4 or 8 bytes."
                    )

            endianness = relative_endianness_resolver(endianness)

            field = cstruct2_float_field(name, width, endianness)

            field.wrapper = wrapper

        elif datatype == "str":
            null: bool = False
            width = data
            encoding = "utf-8"

            if isinstance(data, tuple):
                width = data[0]
                encoding = data[1]

            if width == "null":
                null = True
                self.has_derived_length = True

            if width == "pascal":
                self.has_derived_length = True

            field = cstruct2_string_field(name, width, null)

            field.wrapper = wrapper

        elif datatype == "bytes":
            width = data
            if isinstance(data, tuple):
                width = data[0]
                wrapper = data[1]

            field = cstruct2_bytes_field(name, width)

            field.wrapper = wrapper

        elif datatype == "switch_type":
            switch_obj: switch_type = data

            if switch_obj.dependent not in self.field_names:
                raise cstruct2_switch_dependent_wrong(name, switch_obj.dependent)

            new_switch_obj = switch_type(switch_obj.dependent, {}, name)

            for case, corresponding_field in switch_obj.decisions.items():
                new_switch_obj.decisions[case] = self.metafield_to_field(
                    name,
                    corresponding_field[0].__name__,
                    (
                        tuple(list(corresponding_field)[1:])
                        if len(corresponding_field) > 2
                        else corresponding_field[1]
                    ),
                    anonymous=True,
                )

            self.has_derived_length = True
            field = new_switch_obj

        elif datatype == "cstruct2":
            field = cstruct2_recursive_wrapper(name, value)

            field.wrapper = wrapper
        else:
            raise cstruct2_field_exception(
                f"The field {name} has type {datatype}, which is unrecognizable as a valid cstruct2 field."
            )

        if not isinstance(width, str) and not isinstance(width, int):
            if datatype != "cstruct2" and datatype != "switch_type":
                raise AttributeError(
                    f"The width, {width}, on field {name}, is not int or str."
                )

        # Keep track of derived/variable lengths.
        if isinstance(width, str):
            self.has_derived_length = True

            if not (datatype == "str" and width in ["pascal", "null"]):
                if width not in self.field_names:
                    raise cstruct2_variable_length_exception(name, width)

        # Anonymous fields are returned, instead of being added to the global store.
        # (But they can still reference already processed fields in the global store.)
        # They have only the name of their parent field.
        if anonymous:
            if isinstance(field, list):
                field[0] = name
                return field

            field.name = name
            return field

        # Required to keep track of fields for variable/derived lengths.
        # This is ugly.
        self.fields.append(field)
        self.field_names.append(name)
        self.field_correspondence[name] = field

    def __init__(self, another_class):
        self.__buffer_size = 4096  # 4096 or 8192 are typically good file copying sizes?

        self.obj = another_class
        self.fields = []
        self.field_names: list[str] = []
        self.field_correspondence = {}
        self.members = filter(
            lambda x: not x.startswith("_"), another_class.__dict__.keys()
        )

        self.has_derived_length: bool = False

        # We must count the number of bits taken up by bitfields to report an accurate
        # length of the structure--provided there are no variable lengths.
        self.bit_fields = 0
        self.bit_counter = 0

        # We store the results of each processed field here, which is important
        # so we can have length derived off of the value of other previously processed fields.
        self.values = {}

        self.__parse_meta_fields()

    def __parse_meta_fields(self):
        """
        Given the class that was used to instantiate this one, parse out all of the metaprogramming
        fields and convert them into our internal representation (field object) and then add them to
        our store. Internal function: do not use.
        """

        another_class = self.obj

        for member in self.members:
            annotation: str = another_class.__annotations__[member].__name__
            value = getattr(another_class, member)
            self.metafield_to_field(member, annotation, value)

    def parse_width(self, width: int | str) -> int:
        """
        Parses width parameters. If string and variable, from an existing value in the structure.
        Objects within nested structures can be referenced using a . member accessor operator.
        """

        if isinstance(width, int):
            return width

        tokens = width.split(".")
        current_level = self.values[tokens[0]]

        for i in range(1, len(tokens)):
            current_level = current_level[tokens[i]]

        return current_level[width]

    def parse_field(self, stream, field, recursive=False):
        """
        From a stream of bytes, read out a field from it.
        Returns a value indicating the correctly parsed value, according
        to rules set by the field. If recursive is set, then this won't
        update the internal store of values. Instead, it will return an entirely
        new values dictionary populated with the result of the field parsing.
        """

        values = None
        if not recursive:
            values = self.values
        else:
            values = {}

        wrapper = lambda x: x

        # Tech debt lol!!!111
        if not isinstance(field, list):
            if field.wrapper != None:
                wrapper = field.wrapper

        absolute_width = 0

        # These are objects that do not conform to an abstract field object bearing a determinable length.
        # This is clunky, but it just werkz!!11
        if (
            not isinstance(field, cstruct2_recursive_wrapper)
            and not isinstance(field, switch_type)
            and not isinstance(field, list)
        ):
            absolute_width = field.width

        # Detection for array types.
        if isinstance(field, list):
            absolute_width = field[1]

        # If another type is present, reset the bit counter,
        # as we will need to read another byte into the cache.
        if not isinstance(field, cstruct2_bits_field):
            self.bit_counter = 0

        # Resolve variable width--is it absolute or dependent on another variable?
        if isinstance(absolute_width, str) and not (
            absolute_width in ["null", "pascal"]
        ):
            tmp = absolute_width
            absolute_width = self.values[absolute_width]

            # If the variable length for an int or a float is not within the capable
            # byte lengths for C binary structures.
            if isinstance(field, cstruct2_float_field):
                if absolute_width not in [4, 8]:
                    raise cstruct2_variable_length_absolutely_wrong(tmp, field.name)

            if isinstance(field, cstruct2_int_field):
                if absolute_width not in [1, 2, 4, 8]:
                    raise cstruct2_variable_length_absolutely_wrong(tmp, field.name)

        # A list field represents an array type,
        # which is simply an array of fields that must be evaluated recursively.
        # The list is in the form [resulting field name, number of elements, field in array]
        if isinstance(field, list):
            values[field[0]] = []

            for i in range(absolute_width):
                value = self.parse_field(stream, field[2], True)
                values[field[0]].append(value)

        elif isinstance(field, cstruct2_number_field):
            values[field.name] = wrapper(
                int.from_bytes(stream.read(absolute_width), byteorder=field.endianness)
            )

        elif isinstance(field, cstruct2_float_field):
            data: bytes = stream.read(absolute_width)
            endianness: str = field.endianness_str
            float_size = "d" if absolute_width == 8 else "f"

            values[field.name] = wrapper(
                struct.unpack(f"{endianness}{float_size}", data)[0]
            )

        elif isinstance(field, cstruct2_string_field):
            values[field.name] = ""

            # Null-terminated string has indeterminate length
            if absolute_width == "null":
                while (c := stream.read(1)) != b"\0":
                    values[field.name] += wrapper(c.decode())

            else:
                # Pascal-style strings have a leading byte that describes their length.
                if absolute_width == "pascal":
                    absolute_width = int.from_bytes(stream.read(1))

                # Buffering reads from a stream is more efficient...
                # at least in C it is...
                whole: int = absolute_width // self.__buffer_size
                frac: int = absolute_width % self.__buffer_size

                for i in range(whole):
                    values[field.name] += wrapper(
                        stream.read(self.__buffer_size).decode(field.encoding)
                    )

                if frac:
                    values[field.name] += wrapper(
                        stream.read(frac).decode(field.encoding)
                    )

        elif isinstance(field, cstruct2_bytes_field):
            values[field.name] = wrapper(stream.read(absolute_width))

        elif isinstance(field, switch_type):
            dependent_value = self.values[field.dependent]
            resulting_field = field.decisions[dependent_value]

            # The field name itself of the switch field will be used to store
            # the resulting value of whatever field corresponds to the dependent value

            values[field.name] = self.parse_field(stream, resulting_field, True)

        elif isinstance(field, cstruct2_recursive_wrapper):
            # Recursively parse the other structure.
            tmp = field.another.from_stream(stream)
            values[field.name] = field.wrapper(tmp)

        else:
            ...  # ???

        if recursive:
            return list(values.values())[0]

        return values

    def from_stream(self, stream: RawIOBase) -> dict:
        """
        From any file-like object, read the structure and return a dictionary
        of its high-level, processed contents. Basically a for loop over all fields
        and usage of the parse_field member. Want to read from a bytes object? Seek BytesIO
        """

        # if not issubclass(stream, RawIOBase):
        #    raise TypeError("stream must be a file-like object (derived from RawIOBase)")

        self.values = {}

        try:
            for field in self.fields:
                self.parse_field(stream, field)

        except EOFError:
            raise cstruct2_overflow_exception(None)

        return self.values.copy()

    def from_bytes(self, data: bytes) -> dict:
        """Reads a packed binary structure in the cstruct2 format from a bytes object."""

        stream = BytesIO(bytes)
        return self.from_stream(stream)

    def __ws_value_checker(self, allowed: list, given):
        for good in allowed:
            if isinstance(given, good):
                return

        raise cstruct2_invalid_value_exception(type(given), allowed)

    def write_field(self, values: dict, value, field, stream):
        """
        Write a field to the stream, given the values provided, making sure the value conforms to what the
        corresponding field object says about it.
        """

        absolute_width: int = 0

        # Add provisions for objects that do not support widths
        # Yes, I should have used an abstract base class, instead of throwing all of this
        # together.
        if (
            not isinstance(field, list)
            and not isinstance(field, cstruct2_recursive_wrapper)
            and not isinstance(field, switch_type)
        ):
            absolute_width = field.width

        if isinstance(field, list):
            self.__ws_value_checker([list], value)
            for i in range(field[1]):
                self.write_field(values, value[i], field[2], stream)

        elif isinstance(field, cstruct2_recursive_wrapper):
            self.__ws_value_checker([dict], value)
            field.another.to_stream(value, stream)

        elif isinstance(field, cstruct2_number_field):
            self.__ws_value_checker([int], value)

            data: bytes = int.to_bytes(
                value, absolute_width, byteorder=field.endianness
            )
            if len(data) > absolute_width:
                raise cstruct2_too_big_exception(field.name, absolute_width, len(data))

            stream.write(data)

        elif isinstance(field, cstruct2_float_field):
            float_size = "d" if absolute_width == 8 else "f"
            stream.write(struct.pack(f"{field.endianness_str}{float_size}", value))

        elif isinstance(field, cstruct2_string_field):
            self.__ws_value_checker([str], value)

            data: bytes = value.encode()
            if field.width == "pascal":
                stream.write(int.to_bytes(len(data), "little"))

            stream.write(data)

            # Null terminated string.
            if field.width == "null":
                data += b"\0"

            else:
                if field.width not in ["pascal", "pascal16", "pascal32"]:
                    if len(data) > absolute_width:
                        raise cstruct2_too_big_exception(
                            field.name, absolute_width, len(data)
                        )

                    padding: int = absolute_width - len(data)
                    stream.write(b"\x00" * padding)

        elif isinstance(field, cstruct2_bytes_field):
            self.__ws_value_checker([bytes], value)

            if len(value) > absolute_width:
                raise cstruct2_too_big_exception(field.name, absolute_width, len(value))

            stream.write(value)

            # Apply padding if necessary.
            if (absolute_width - len(value)) > 0:
                stream.write(b"\x00" * absolute_width - len(value))

        elif isinstance(field, switch_type):
            actual_field = field.decisions[values[field.dependent]]
            self.write_field(values, value, actual_field, stream)

        else:
            ...

    def to_stream(self, values: dict, stream: RawIOBase):
        """Given a dictionary of values conforming to this structure, write it to a stream."""

        try:
            # For each key in the values provided, find out what fields they're supposed to be
            # so we can write the correct value to the stream.

            for key, value in values.items():
                if key not in self.field_names:
                    raise cstruct2_non_existent_field_exception(key)

                self.write_field(values, value, self.field_correspondence[key], stream)

        except:
            ...

    def to_bytes(self, values: dict) -> bytes:
        """Converts the values corresponding to the field values to a bytes object."""

        output = BytesIO()
        self.to_stream(values, output)
        return output.read()

    def set_buffer_size(self, size: int):
        """
        If you're unhappy with the default buffer size (4096), set it here.
        Just consider that too low and too high are both bad, and it's hard to get right.
        """

        self.__buffer_size = size

    def __len__(self) -> int:
        if self.has_derived_length:
            raise cstruct2_indeterminate_length_exception()

        result = 0

        # Switch cases are not supported because they are, by definition, indeterminate at
        # structure initialization time.
        for field in self.fields:
            if isinstance(field, cstruct2_recursive_wrapper):
                result += len(field.another)
                continue

            result += field.width

        result += math.ceil(self.bit_fields / 8)
        # ~~~~~~~~~~~~~^ it's ceiling-ed because if we only read 4 bits, we've still read a byte.
        # Likewise, if we read 12 bits, we've definitely read a byte (8 bits) but then read an extra 4 bits,
        # which is another byte!


structure = Structure
