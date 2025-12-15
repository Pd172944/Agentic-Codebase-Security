import os

# Path to the controller file on your Mac
file_path = "/Users/prithvidixit/Desktop/cs194Application/194-2new/venv/lib/python3.14/site-packages/agentbeats/controller.py"

print(f"🔧 Patching Controller at: {file_path}")

try:
    with open(file_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    patched = False

    for line in lines:
        new_lines.append(line)
        
        # We look for the line where AGENT_URL is set in the subprocess environment
        # and we inject our CLOUDRUN_HOST override immediately after it.
        if 'env["AGENT_URL"] =' in line and not patched:
            indent = line[:line.find('env')]
            
            # This logic ensures the agent sees the full path (domain + /to_agent/id)
            # instead of just the root domain.
            new_lines.append(f'{indent}# FORCE FIX: Override CLOUDRUN_HOST to include the full path\n')
            new_lines.append(f'{indent}env["CLOUDRUN_HOST"] = f"{{_host}}{{_port_s}}/to_agent/{{agent_id}}"\n')
            
            patched = True
            print("   -> Injected CLOUDRUN_HOST override.")

    if patched:
        with open(file_path, "w") as f:
            f.writelines(new_lines)
        print("✅ Controller patched successfully!")
    else:
        print("⚠️ Could not find the insertion point. Is the file already patched?")

except FileNotFoundError:
    print("❌ Error: File not found. Please check the path.")
