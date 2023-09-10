from cstruct2.cstruct2 import cstruct2, struct

@cstruct2
class User:
    id: int = 1
    username_len: int = 2
    username: str = "username_len"


@cstruct2
class ReadTest:
    number: int = 4
    string: str = 16
    user_len: int = 4
    users: struct = ["user_len", User]


with open("read-test.bin", "rb") as fp:
    print(ReadTest.from_stream(fp))