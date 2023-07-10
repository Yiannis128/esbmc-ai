#include <stdlib.h>
#include <assert.h>

#define NUM_ONE 1
#define NUM_TWO 2

struct linear
{
    int value;
};

typedef struct linear LinearTypeDef;

typedef struct
{
    int x;
    int y;
} Point;

Point a;
Point *b;

int c;

char *d;

typedef enum Types
{
    ONE,
    TWO,
    THREE
} Typest;

enum Types e = ONE;

Typest f = TWO;

union Combines
{
    int a;
    int b;
    int c;
};

typedef union Combines CombinesTypeDef;

int main()
{
    Point *a = (Point *)malloc(sizeof(Point));
    if (a != NULL)
        return -1;
    free(a);
    return 0;
}