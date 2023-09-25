# *cstruct2*

Version: 1.0.1 (Beta)

*cstruct2* is a Python library that hopes to simplify and ease the experience of working with C-style packed binary structures. That is, if you were to directly write the memory of a packed (not padded, there's a difference!) structure in C to a file, this library would be able to hasslelessly read them. There exists a myriad of other means to do this in Python, such as reading each byte by hand or using Python's native *struct* library, but these are clunky and hard to read solutions. *cstruct2* provides a metaprogramming interface, wherein you define a class decorated by *cstruct2* that defines each field to be read, in an intelligent way.

The reading of fields of a certain type and explicit width is a given, but *cstruct2* allows you to base a field's length off of the value of another previously read field, making code easier to write and read. Not only that, you can tell a *cstruct2* decorated object to read a *different* field based off of the value of a previously read field, which is highly convenient if you're trying to parse a dusty network protocol (SOCKS5 comes to mind). Of course, it wouldn't be complete without allowing you to recursively read nested *cstruct2* objects within one another, which *cstruct2* allows you to do! There's more than that, of course, but those are the main highlights and superiorities of *cstruct2*.

## Basic Usage

Each field is a member of a decorated class, where the type of the data item is given as a type annotation and the value of that data item is its size, in most cases. For example, if we wanted to define an object *MyStructure* which has an integer 4 bytes in length--*cstruct2* assumes Little Endian ordered integers--and an ASCII string 32 bytes in length:

    from cstruct2.cstruct2 import cstruct2
        
    @cstruct2
    class MyStructure:
	    my_number: int = 4
	    my_string: str = 32
   	  

Every *cstruct2* derived structure will then immediately be instantiated upon invoking its name, where a *.from_stream()* member will be exposed. One will call this method with a Python *file*-like object, most importantly an object with the *read()* method for reading bytes in a stream. This can be from a socket, from an actual file, from a BytesIO or StringIO object, or anything really. Upon invoking this member on such an object, a dictionary will be returned with the values read. In the example above, the following dictionary is within the realm of possibility upon the *.from_stream()* member being called:

    with open("file.bin", "rb") as fp:
	    print(MyStructure.from_stream(fp))

	-->

    {
		"my_number": 256,
		"my_string": "This is a string."
	}


## Primitive Types and Variable Length

Because we are dabbling in the wonders of Python metaprogramming, we've kind of created our own mini programming language. *cstruct2* has a few primitive types, which are just simple standard data types that have a length and can be read in. *cstruct2* currently supports the following primitive types, which are denoted on each field as a Python type annotation:

 - *str* - Any kind of string, could be encoded in a myriad of different ways.
 - *int* - Any kind of integer, which can be encoded in either Little or Big Endian, with differing widths.
 - *float* - Any kind of floating point number, with widths 4 or 8 bytes and differing endianness.
 - *bits* - Any arbitrary number of bits to be read in, in the style of C structures, where a new byte is read in whenever a new bitfield has appeared or 8 consecutive bits have been read. **This is currently not fully operational, so don't rely on it.**
 - *bytes* - An arbitrary number of bytes, where a Python *bytes* objects will be returned to store the bytes.
 - (Future) (For writing only) *anyfield*: allows any type to be written to a stream with the structure, with the field being provided at runtime. When declaring this in the structure, it must be initialized to *None*. *cstruct2* will throw an exception if this field is in a structure that is reading from a stream. When writing the structure to a stream, this field's value in the data dictionary must be a tuple of *(field tuple, value)*. 

Already, if you've been paying attention, we've encountered a problem. With all of the variations described above, how can we tell *cstruct2* about all of them, with one value in the object field declaration? If we want to get more specific about our field, we will have to make its value a tuple, a tuple of more specific information in addition to the field's width. For example, if we want to read in an integer worth 2 bytes but encoded as Big Endian, we'd have to declare:

    @cstruct2
    class MyStructure:
	    number: int = ("big", 2)

Now the question is, what are the available options for settings in tuples, and what are their orders, for each primitive data type? Below, we will list the different settings, exceptions, and orders for each data type, when using them in tuple-form:

 - *str*: (*length*, *encoding*, *wrapper*)
	 - The *encoding* field may be any string encoding value that Python uses when decoding strings (e.g., "utf-8" or "ascii"). 
	 - If *length* is "null"--and this is really important--then a null-terminated string will be read in. That is, *cstruct2* will keep reading bytes until it gets a '\0' byte.
	 - If *length* is "pascal", then the string's length will be determined by the first byte that precedes it, as in a Pascal-style string.
	 - (Future): If *length* is "pascal16" or "pascal32", then the same as regular "pascal" above, but with 16 bit and 32 bit lengths.
 - *int*: (*endianness*, *length*, *wrapper*)
	 - *endianness* can be explicitly declared by using "big" or "little", but "host" and "network" are both options, which are relative endianness options.
 - *float*: (*endianness*, *length*, *wrapper*)
	 - *endianness* has the same string enumerations as above.
 - *bytes*: (*length*, *wrapper*)
 - *bits*: (*length*, *wrapper*)
 - (Future) (For writing only) *anyfield*: *Structure value required to be None*

You may have noticed a *wrapper* field at the end of every tuple, along with how it was left unexplained in each bullet-point. The *wrapper* field allows you to pass in an object or a function that will receive the read in field and will convert it to another object or datatype afterwards, when it finally puts it into the resulting dictionary, if in structure reading mode. For example, if we want to read in a *str* but then want to cast it to our custom *User* class:

    class User:
	    def __init__(self, usr: str):
		    self.usr = usr
    
    @cstruct2
    class MyStructure:
	    username: str = ("null", User)


Pretty cool. But what if your C structure first sends a *uint16_t* describing the number of bytes that the next string it sends will be? When parsing that manually, you can very easily become confused. However, *cstruct2* allows you to base the length of a later field on the currently read value of a prior field, by simply referencing that field as a string when you pass in a *str* as a length argument. For example:

    @cstruct2
    class MyStructure:
	    len: int = ("little", 2)
	    string: str = "len"

This is the power of variable/derived lengths in *cstruct2*--and it's simply amazing. Anywhere a field is supposed to have a length or a width, you can simply pass in a string that references a previously read field, PROVIDED that the field is an integer type within the *cstruct2* decorated structure. It doesn't matter if you cast the field later on to an *int* by cleverly using wrappers, it **must** be an *int* field within the structure.

## Arrays

Of course, no structure parsing library is complete without the ability to read repeated elements, based off of another field's value. Very commonly are we asked to read in *n* items when dealing with such structures. Simply, arrays in *cstruct2* are declared by setting the field's value to that of a list, where the length of the array is the first element, then the settings of the underlying element(s) in the second and onward elements. For example:

    

	class User:
	    def __init__(self, usr: str):
		    self.usr = usr
		    
	@cstruct2
    class MyStructure:
	    no_names: int = 4
	    names: str = [
		    "no_names",
			16,
			User
	    ]

This structure will read in *no_names* number of 16 byte strings, which will then all be casted to *User* objects, since that is what the wrapper was set to in the *str* field's options. 

The resulting dictionary may look something like this:

    {
	    "no_names": 3,
	    "names": [
		    <User obj blah blah 1>,
		    <User obj blah blah 2>,
		    <User obj blah blah 3>
	    ]
    }

If one wants to wrap the resulting array into something, then the last argument of the list describing the array should be a callable type which then returns the wrapper, in the same way any other field can be wrapped.

## Switch Fields

It is also very common for the field we read to be different based off of the value of another previously read field. If the SOCKS5 protocol tells us the address type can be IPv4, IPv6, or a string domain, we need to have some variability in our code. This is exactly what a switch field allows us to do.

A switch field is made by declaring a field to be that of a *switch* type, then the value being a switch object which has two instantiation arguments:

 - *dependent_value*: str, the previously read field we base our decisions on
 - *decisions*: dict, a map of what each value as read from *dependent_value* should be as a another *cstruct2* field.

Due to the nature of the declared switch statement, the field type cannot be given as a type annotation. Instead, it must be given as the first argument of a tuple describing each possible field in a decision mapping. Of course, the last argument of the tuple for each decision field would describe a wrapper.

Of course, with things like these, it's best to explain additionally with just an example:

    from cstruct2.cstruct2 import cstruct2, switch
    
    @cstruct2
    class MyStructure:
	    usr_type: int = 1
	    user: switch = switch(
		    "usr_type", {
			    0: (int, "little", 4),
				1: (str, "null"),
				2: (int, [3, "big", 8])
			}
		)

The structure is saying: if *usr_type* is equal to 0, then read in a Little Endian 4 byte integer and place that into *user* when we're done; if *usr_type* is equal to 1, then read in a null terminated string; finally, if *usr_type* is equal to 2, then read in an array of ints 2 elements in length, where each integer is a Big Endian 8 byte integer. Wow, would that be a nightmare to manually write!

## Nested *cstruct2* structures

As with C structures, we can have nested *cstruct2* structures, where the result will be placed in a subobject in the main dictionary that parsing would yield. The field's type annotation for a nested *cstruct2* structure must be that of *structure*, with the value equal to the *cstruct2* object representing that nested structure--and if you use a tuple, the last argument of that tuple would be some wrapper which would be fed the corresponding read dictionary of the nested structure. An example only will be provided, because it's crystal clear how it works:

    from cstruct2.cstruct2 import cstruct2, structure
    
    @cstruct2
    class UserStructure:
	    id: int = 4
	    username_len: int = ("big", 2)
	    username: str = "username_len"
    
    @cstruct2
    class MainStructure:
	    code: int = 1
	    users_len: int = 2
	    users: structure = [
		    "users_len",
		    UserStructure
	    ]

The resulting dictionary may look like something like this:

    {
    	"code": 27272727,
    	"users_len": 2,
    	"users": [
    		{
				"id": 1,
				"username_len": 5,
				"username": "hello"
			},
			{
				"id": 2,
				"username_len": 6,
				"username": "hello2"
			}
        ]
    }

It's breathtaking, if you've ever toiled away parsing packed binary structures manually. The amount of bugs, the amount of headaches, and the amount of silly mistakes...  Let's write some C code to compare!

    struct __attribute__((__packed__)) UserStructure {
    	uint64_t id;
    	uint16_t length;
    };
    
    struct __attribute__((__packed__)) MainStructure {
    	uint8_t code;
    	uint16_t users_len;
    };
    
    ...
    
    int main(void) {
    	FILE *fp = fopen("file.bin", "rb");
    	
    	struct MainStructure mstruct;
		fread(&mstruct, 1, sizeof(mstruct), fp);
		for (uint16_t i = 0; i < mstruct.users_len; i++) {
			struct UserStructure ustruct;
			fread(&ustruct, 1, sizeof(ustruct), fp);
			uint16_t little_len = ntohs(ustruct.username_len);
			char *username = (char*) malloc(ustruct.little_len + 1);
			fread(username, 1, ustruct.little_len, fp);
			username[ustruct.little_len] = '\0';
			
			printf("[%d]: (%d) %s", i, ustruct.id, username);
			free(username);
		}

		fclose(fp);
    	return 0;
    }

The manual Python version, if you're not using *struct*, is not much better (and in fact, can be longer!). 

## Writing Structures

It's natural to also want to write these structures back to a stream or to some other output, so naturally *cstruct2* supports it. Writing structures isn't scattered throughout the previous sections because it does not differ much from regular *cstruct2* structure reading mode. There are some minute differences, but they are minute enough to be all under one inclusive section.

A *cstruct2* parsed structure will have the *to_stream()* and *to_bytes()* methods that will write the structure to either a stream or will write it to bytes which will be returned. In both of those methods, a dictionary containing the values for each defined field must be passed as the first argument. Obviously, *to_stream()* then needs the stream as its second argument. Let's give an example:

    @cstruct2
    class MyStructure:
    	age: int = ("little", 4)
    	name: str = "null"
    	things: int = [3, "little", 2]
    
    with open("out.bin", "wb") as fp:
    	MyStructure.to_stream({
			"age": 32,
			"name": "Test Person",
			"things": [2, 3, 5]
        }, fp)

This will write the values to the corresponding fields to the stream provided, which points to a file. Because of how the structure was defined, *age* will be written as a 4 byte integer in Little Endian order to the stream. Similarly, *name* will be written as a null terminated string to the stream... you get the picture now.

## Auxiliary Components

*cstruct2* provides some wrapper classes and helper functions in its library, most notably *cstruct2.cstruct2.SocketWrapper*. If you want to read or write a structure from/to a socket, you will need to construct a *SocketWrapper* on that socket first, before utilizing it with *cstruct2*. For example, if I open a socket as a client, and I wish to utilize it with *cstruct2*:

    from cstruct2.cstruct2 import cstruct2
    from cstruct2.cstruct2_utils import SocketWrapper
    
    @cstruct2
    class Handshake:
    	id: int = ("little", 4)
    	username: str = "pascal"
    	password: str = "pascal"
    
    @cstruct2
    class Response:
    	last_login: int = ("little", 8)
    	messages_len: int = ("little", 2)
    	messages: str = ["messages_len", "null"]
    
    sock = socket.socket()
    sock.connect(("192.168.0.3", 8080))
    sock_wrapper = SocketWrapper(sock)
    
    Handshake.to_stream({
    	"id": 321,
    	"username": "admin",
    	"password": "123"
    }, sock_wrapper)
    
    response: dict = Response.from_stream(sock_wrapper)
    for msg in response["messages"]:
    	print(msg)
    
    sock.close()

A variety of examples are provided in this repository, such as an example SOCKS5 proxy server created with *cstruct2* and a C program that writes packed binary structures to a file, which *cstruct2* will then read and parse.

## Miscellaneous

A list of changes to this library can be seen through the CHANGELOG	file in this repository. A list of things that need to get done can be seen through the TODO file that is also in this repository. The source code to this library is quite messy and inefficient at the moment as well, as a heads up. If you have any questions, complaints, or suggestions, feel free to make issues on this repository or email me at arner@usa.com.

	

  


