from cstruct2.cstruct2 import cstruct2, struct


@cstruct2
class DataStructure:
    name: str = 16
    age: int = 4
    values: str = [3, 10]


with open("write_test.bin", "wb") as fp:
    DataStructure.to_stream({
        "name": "hey",
        "age": 82,
        "values": [
            "hey",
            "whatever",
            "new"
        ]
    }, fp)