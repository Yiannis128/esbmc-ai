#define NULL 0

struct LinkedList
{
    int value;
    struct LinkedList *next;
};

struct LinkedList *get_from_index(struct LinkedList *root, int index)
{
    if (index < 0 || !root)
    {
        return NULL;
    }

    struct LinkedList *ptr = root;
    while (index > 0)
    {
        if (!ptr->next)
        {
            return NULL;
        }

        ptr = ptr->next;
        index--;
    }
    return ptr;
}

int main()
{
    return 0;
}