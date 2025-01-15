# utils/navigation.py
def navigate_to_path(structure, path):
    current = structure
    for folder in path:
        current = current["folders"][folder]
    return current
