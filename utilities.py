def r_update(base_dict, update_dict):
    """Recursively updates dictionary"""
    for key in base_dict.keys():
        new_val = update_dict.get(key, None)
        if isinstance(new_val, dict):
            r_update(base_dict[key], new_val)
        elif new_val:
            base_dict[key] = new_val
        else:
            continue
    for key in update_dict.keys():
        if key in base_dict.keys():
            continue
        else:
            base_dict[key] = update_dict[key]
    return base_dict

def btwn(number, bounds):
    "Checks if number is within bounds"
    if number > min(bounds) and number < max(bounds):
        return True
    else:
        return False

def splice(base_list, new_list, splice_idx):
    return base_list[:splice_idx] + new_list + base_list[splice_idx:]

def replace(base_list, new_element, replace_idx):
    if not isinstance(new_element, list):
        new_element = [new_element]
    return base_list[:replace_idx] + new_element + base_list[replace_idx + 1 :]

def max_none(iterable):
    """Gets maximum value of iterable. If iterable is None or empty, returns 0."""
    if iterable:
        return max(iterable)
    else:
        return 0

def get_orientation(side):
    if side in ['left', 'right']:
        return 'horizontal'
    elif side in ['top', 'bottom']:
        return 'vertical'
    else:
        raise ValueError("Invalid side name")

def strip_comments(line_list):
    """Removes comments from lines."""
    import re
    new_line_list = []
    multiline_comment = False

    # Precompile RegEx patterns
    slineA = re.compile("//")
    slineB = re.compile("/\*[\w\W]+\*/")
    mline_begin = re.compile("/\*")
    mline_end =  re.compile("\*/")
    empty = re.compile("(?![\s\S])")

    # Line-by-line Comment Filter
    for line in line_list:
        # Remove single line comment
        if re.search(slineA, line):
            continue
        # Remove single line comment defined with /* ... */ syntax
        elif re.match(slineB, line):
            continue
        # Remove first line of multiline comment and begin tracking
        elif re.search(mline_begin, line):
            multiline_comment = True
            continue
        # Remove lines that are in the body of the multiline comment
        elif multiline_comment and not re.search(mline_end, line):
            continue
        # Remove last line of multiline commend and stop tracking
        elif re.search(mline_end, line):
            multiline_comment = False
            continue
        # Remove empty lines
        elif re.match(empty, line):
            continue
        else:
            new_line_list.append(line)
    return new_line_list