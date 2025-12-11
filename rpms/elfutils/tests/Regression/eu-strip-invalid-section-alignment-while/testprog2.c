static unsigned char buffer[4096] __attribute((aligned (4096)));
char
f (int i)
{
    return buffer[i];
}

int
main (int argc, char **argv)
{
    return buffer[argc] == 0;
}
