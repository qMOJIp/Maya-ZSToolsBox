import re

def GN_IsValidObjectName(name):
    '''
    Check if the string is a valid object name.
    A valid object name begins with a letter or underscore and is followed
    with letters, digits, or underscores. Spaces are not allowed.
    '''

    regex = "^[^\w_]|^[\d]|[^\w\d_]"
    return re.match(regex, name)

def GN_EncodeName(name):
    '''
    Returns a valid object name.
    A valid object name begins with a letter or underscore and is followed
    with letters, digits, or underscores. Spaces are not allowed.
    '''

    regex = "^[^\w_]|^[\d]|[^\w\d_]"
    name = re.sub(regex, "_", name)
    return name


def GN_IncrementName(name, spacing=""):
    m = re.search(r"\d+$", name)
    if m:
        num = m.group()
        num = str(int(num) + 1).zfill(len(num))
        k = m.span()[0]
        increment = m.string[:k] + spacing + num
    else:
        increment = f"{name}{spacing}1"
    
    return increment