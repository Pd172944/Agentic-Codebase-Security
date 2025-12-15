import os
import re

# The path to your broken file
file_path = "/Users/prithvidixit/Desktop/cs194Application/194-2new/venv/lib/python3.14/site-packages/agentbeats/myutils.py"

print(f"🔧 Repairing {file_path}...")

# 1. Read the current file content
try:
    with open(file_path, "r") as f:
        content = f.read()
except FileNotFoundError:
    print("❌ Error: File not found. Check the path.")
    exit(1)

# 2. Define the BROKEN function pattern (we will look for the start of the function)
#    and replacing the whole block is tricky with regex, so we'll replace the known bad area.
#    However, rewriting the whole function text is safer.

# This is the CLEAN, CORRECT version of the function with 4-space indentation.
clean_function = """async def send_a2a_message(
    url, message, task_id=None, context_id=None
) -> SendMessageResponse:
    httpx_client = httpx.AsyncClient(timeout=1800.0)
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)
    card: AgentCard | None = await resolver.get_agent_card()
    
    # FORCE FIX: Override card URL to prevent 405 Redirect Error
    if card:
        card.url = url

    client = A2AClient(httpx_client=httpx_client, agent_card=card)
    message_id = uuid.uuid4().hex
    params = MessageSendParams(
        message=Message(
            role=Role.user,
            parts=[Part(TextPart(text=message))],
            message_id=message_id,
            task_id=task_id,
            context_id=context_id,
        )
    )
    request_id = uuid.uuid4().hex
    req = SendMessageRequest(id=request_id, params=params)
    response = await client.send_message(request=req)
    return response"""

# 3. We will find the function definition in the file and replace it entirely.
#    This regex looks for 'async def send_a2a_message' and captures everything until 'def kickoff'.
pattern = re.compile(r"async def send_a2a_message\(.*?\n\)\s*->\s*SendMessageResponse:.*?return response", re.DOTALL)

# Check if we can find the function to replace
match = pattern.search(content)

if match:
    # Perform the replacement
    new_content = content.replace(match.group(0), clean_function)
    
    # Write the fixed content back
    with open(file_path, "w") as f:
        f.write(new_content)
    print("✅ Function 'send_a2a_message' has been completely rewritten with correct indentation.")
else:
    print("⚠️ Could not find the function via Regex. Falling back to manual overwrite.")
    
    # FALLBACK: If the file is too messed up for regex, we look for the header and truncate/rewrite manually.
    # This assumes standard file structure.
    lines = content.splitlines()
    new_lines = []
    skip = False
    
    for line in lines:
        if "async def send_a2a_message" in line:
            # We found the start, insert our clean version
            new_lines.append(clean_function)
            skip = True # Start skipping the old broken lines
        
        if "def kickoff" in line:
            skip = False # Stop skipping when we hit the next function
            
        if not skip:
            new_lines.append(line)
            
    with open(file_path, "w") as f:
        f.write("\n".join(new_lines))
    print("✅ Fallback repair complete.")

print("🚀 You can now run 'agentbeats run_ctrl'")
