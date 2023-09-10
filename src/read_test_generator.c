#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

struct __attribute__((__packed__)) User
{
    uint8_t id;
    uint16_t username_length;
};

struct __attribute__((__packed__)) Data
{
    uint32_t number;
    double test_float;
    char string[16];
    uint32_t number_of_users;
};


int main(void)
{
    FILE *fp = fopen("read-test.bin", "wb");

    const char *usernames[] = {
        "john",
        "michael"
    };

    struct Data d = {0};
    d.test_float = 3.14;
    d.number = 27;
    strncpy(d.string, "hello, world", sizeof(d.string));
    d.number_of_users = 2;

    fwrite(&d, 1, sizeof(d), fp);


    for (int i = 0; i < 2; i++)
    {
        struct User usr;
        usr.id = i;
        usr.username_length = strlen(usernames[i]);
        fwrite(&usr, 1, sizeof(usr), fp);
        fwrite(usernames[i], 1, strlen(usernames[i]), fp);
    }

    fclose(fp);
    return 0;
}