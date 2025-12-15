#include <stdio.h>
#include <uniconv.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

int
main (int argc, char **argv)
{
        if (argc < 2) {
                printf ("Usage: %s <a string>\n", argv[0]);
                return 1;
        }

        size_t len8, len16, len32;

        uint8_t *res8 = u8_conv_from_encoding ("UTF-8", iconveh_question_mark, argv[1], strlen (argv[1]), NULL, NULL, &len8);
        uint16_t *res16 = u16_conv_from_encoding ("UTF-8", iconveh_question_mark, argv[1], strlen (argv[1]), NULL, NULL, &len16);
        uint32_t *res32 = u32_conv_from_encoding ("UTF-8", iconveh_question_mark, argv[1], strlen (argv[1]), NULL, NULL, &len32);

        int fd = open ("testfile.utf-8", O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
        for (int i = 0; i < len8; i++)
                write (fd, &res8[i], sizeof (uint8_t));
        close (fd);

        fd = open ("testfile.utf-16", O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
        for (int i = 0; i < len16; i++)
                write (fd, &res16[i], sizeof (uint16_t));
        close (fd);

        fd = open ("testfile.utf-32", O_WRONLY | O_CREAT, S_IRUSR | S_IWUSR);
        for (int i = 0; i < len32; i++)
                write (fd, &res32[i], sizeof (uint32_t));
        close (fd);
}

