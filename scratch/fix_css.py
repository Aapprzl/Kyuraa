
import os

filepath = r'd:\PROJECT_APP\Kyuraa\src\gateway\static\style.css'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We want to remove lines 1711 and 1712 (1-based)
# which are index 1710 and 1711
if len(lines) >= 1712:
    # Double check if they are the orphans
    if 'overflow: hidden;' in lines[1710] and lines[1711].strip() == '}':
        print(f"Removing orphan lines: {lines[1710].strip()} and {lines[1711].strip()}")
        del lines[1711]
        del lines[1710]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print("Success")
    else:
        print(f"Mismatch! Line 1711 is: '{lines[1710].strip()}', Line 1712 is: '{lines[1711].strip()}'")
else:
    print("File too short")
