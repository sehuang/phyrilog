def r_update(base_dict, update_dict):
    """Recursively updates dictionary"""
    for key in base_dict.keys():
        new_val = update_dict.get(key, None)
        if isinstance(new_val, dict):
            r_update(base_dict[key], update_dict[key])
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