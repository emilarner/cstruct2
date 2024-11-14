from cstruct2.decorator import Structure, structure


@Structure
class User:
    id: int = 1
    username_len: int = 2
    username: str = "username_len"


@Structure
class ReadTest:
    number: int = 4
    test_float: float = 8
    string: str = 16
    user_len: int = 4
    users: structure = ["user_len", User]


with open("read-test.bin", "rb") as fp:
    print(ReadTest.from_stream(fp))
