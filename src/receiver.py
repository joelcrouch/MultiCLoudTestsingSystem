import asyncio
from aiohttp import web
import json
from datetime import datetime
import os # NEW IMPORT

# Define a global variable for the output file path
OUTPUT_FILE = os.environ.get("RECEIVER_OUTPUT_FILE", "/tmp/receiver_output.jsonl") # NEW

async def handle_message(request):
    """
    Handles incoming messages (data chunks) from the CrossCloudCommunicationProtocol.
    """
    try:
        data = await request.json()
        sender_id = data.get("sender_id", "unknown")
        message_type = data.get("message_type", "unknown")
        payload = data.get("payload", {})
        chunk_data = payload.get("chunk_data", "no_chunk_data")

        print(f"[{datetime.now()}] Received message from {sender_id}:")
        print(f"  Type: {message_type}")
        print(f"  Chunk Data (first 50 chars): {chunk_data[:50]}...")
        print(f"  Payload keys: {payload.keys()}")

        # Write received data to a file for test verification
        with open(OUTPUT_FILE, "a") as f: # NEW
            json.dump({"sender_id": sender_id, "message_type": message_type, "chunk_data_len": len(chunk_data)}, f) # NEW
            f.write("\n") # NEW

        return web.Response(text="Message received successfully", status=200)
    except json.JSONDecodeError:
        print(f"[{datetime.now()}] Received invalid JSON.")
        return web.Response(text="Invalid JSON", status=400)
    except Exception as e:
        print(f"[{datetime.now()}] Error handling message: {e}")
        return web.Response(text=f"Error: {e}", status=500)

async def start_receiver():
    """
    Starts the aiohttp web server to listen for incoming messages.
    """
    app = web.Application(client_max_size=1024*1024*100) # NEW: Set max size to 100MB
    app.router.add_post('/message', handle_message)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    print(f"[{datetime.now()}] Starting receiver on http://0.0.0.0:8080")
    await site.start()
    # Keep the server running indefinitely
    while True:
        await asyncio.sleep(3600) # Sleep for an hour, or until interrupted

if __name__ == "__main__":
    try:
        asyncio.run(start_receiver())
    except KeyboardInterrupt:
        print(f"[{datetime.now()}] Receiver stopped.")
