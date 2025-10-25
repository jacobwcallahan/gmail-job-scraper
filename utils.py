def update_value(file_path, key, new_value):
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

