class cstruct2_too_big_exception(Exception):
    def __init__(self, name, defined_width: int, given_width: int):
        super().__init__(
            (
                f"{name} has a defined width of {defined_width} bytes/bits, but you passed in "
                f"{given_width} bytes/bits, which is more than the field's capacity."
                f"Is your field's width variable? Are you encoding your string as UTF-16/32?"
            )
        )


class cstruct2_invalid_value_exception(Exception):
    def __init__(self, value_type: str, allowed_types: list[str]):
        super().__init__(
            (
                f"Value {value_type} passed in when only types"
                " ".join(allowed_types) + "are allowed."
            )
        )


class cstruct2_non_existent_field_exception(Exception):
    def __init__(self, field_name: str):
        super().__init__(f"The field '{field_name}' does not exist.")


class cstruct2_variable_length_exception(Exception):
    """This is raised when a variable's variable length is derived from something that comes after it."""

    def __init__(self, length_user: str, length_from: str):
        msg: str = (
            f"{length_user} is trying to get a length from {length_from}"
            f" but {length_from} comes after {length_user}. This is not allowed."
        )

        super().__init__(msg)


class cstruct2_variable_length_wrong(Exception):
    """This is raised when the variable length does not point to an integer or bitfield."""

    def __init__(self, offender: str, victim: str):
        msg: str = (
            f"{offender} is trying to derive its length from {victim}, but"
            f" {victim} is NOT an integer type."
        )

        super().__init__(msg)


class cstruct2_variable_length_absolutely_wrong(Exception):
    def __init__(self, dependent: str, offender: str):
        msg: str = (
            f"When trying to read the variable length for a variable int or float, named "
            f"'{offender}', "
            f"the length given by '{dependent}' was not 1, 2, 4, 8 (for ints) or "
            f"4 or 8 for floats. This is catastrophic."
        )

        super().__init__(msg)


class cstruct2_indeterminate_length_exception(Exception):
    """
    If you have types that are dependent on other types for length, this is raised because we
    cannot calculate structure size without actually parsing such a structure.
    """

    def __init__(self):
        super().__init__(
            "Because the structure uses variable lengths, the length cannot be determined beforehand."
        )


class cstruct2_overflow_exception(Exception):
    """This is raised when the structure reading goes beyond the bounds of the file."""

    def __init__(self, violator: str):
        super().__init__(
            f"When reading {violator}, we read past the file... is your structure or file correct?"
        )


class cstruct2_field_exception(Exception):
    """This is raised when a field is incorrectly declared."""

    def __init__(self, msg: str):
        super().__init__(msg)


class cstruct2_switch_dependent_wrong(Exception):
    """This is raised when a switch case is dependent on something that doesn't exist (yet?)"""

    def __init__(self, offender: str, victim: str):
        super().__init__(
            (
                f"The switch field {offender} tries to determine its route through {victim}"
                f" but {victim} either comes after {offender} or doesn't exist at all!"
            )
        )
