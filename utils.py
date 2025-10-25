def update_value(file_path, key, new_value):
    """
    Update a value in a config file.

    Args:
        file_path: The path to the config file.
        key: The key to update.
        new_value: The new value to set.
    """
    lines = []
    found = False

    with open(file_path, "r") as f:
        for line in f:
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={new_value}\n")
                found = True
            else:
                lines.append(line)
    
    if not found:
        lines.append(f"{key}={new_value}\n")

    with open(file_path, "w") as f:
        f.writelines(lines)

