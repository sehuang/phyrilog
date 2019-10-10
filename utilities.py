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