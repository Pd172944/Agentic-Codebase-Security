import os

# The file causing the crash
file_path = "/Users/prithvidixit/Desktop/cs194Application/194-2new/venv/lib/python3.14/site-packages/agentbeats/myutils.py"

print(f"Sanitizing indentation in: {file_path}")

try:
    with open(file_path, "r") as f:
        content = f.read()

    # Convert every TAB character into 4 SPACES
    new_content = content.replace("\t", "    ")

    if new_content != content:
        with open(file_path, "w") as f:
            f.write(new_content)
        print("✅ Success! Tabs converted to spaces. You can run agentbeats now.")
    else:
        print("ℹ️ No tabs found. The indentation might be malformed in another way (e.g., 3 spaces vs 4).")
        # If simple tab replacement didn't work, let's force normalize indentation on that specific block
        lines = content.splitlines()
        fixed_lines = []
        for line in lines:
            # Fix the specific lines we added if they are weird
            if "card.url = url" in line:
                # Force 4 spaces of indentation
                fixed_lines.append("    if card:")
                fixed_lines.append("        card.url = url")
                # Skip the "if card:" line if we encounter it in the loop to avoid duplication
                continue 
            if "if card:" in line and "card.url = url" not in line:
                 continue
            
            fixed_lines.append(line)
        
        # This fallback is a bit risky blindly, so let's stick to the tab replace first.
        # If the user still has issues, I will provide the raw file content to overwrite.

except FileNotFoundError:
    print("❌ Error: File not found at that path.")
