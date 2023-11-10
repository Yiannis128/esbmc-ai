// ESBMC: https://github.com/esbmc/esbmc/blob/master/src/c2goto/library/string.c

#include <stddef.h>

char *strncpy(char *dst, const char *src, size_t n)
{
__ESBMC_HIDE:;
    char *start = dst;

    while (n && (*dst++ = *src++))
        n--;

    if (n)
        while (--n)
            *dst++ = '\0';

    return start;
}

int main()
{
    return 0;
}