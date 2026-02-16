# ... (Imports remain the same) ...

# ... (Keep get_file_details and verify_password as they are) ...

@router.get("/dl/{unique_id}")
async def stream_handler(unique_id: str, request: Request, token: str = Query(None), expires: int = Query(None)):
    # 1. Security Check
    message = f"{unique_id}{expires}"
    expected = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected, token or "") or int(time.time()) > int(expires or 0):
        raise HTTPException(status_code=403, detail="❌ Link Expired")

    # 2. Find File
    file_data, _ = await find_file(unique_id)
    if not file_data: raise HTTPException(status_code=404, detail="File not found")

    # 3. Select Client
    owner_bot_id = file_data.get("bot_id")
    if owner_bot_id and owner_bot_id in RUNNING_CLONES:
        active_client = RUNNING_CLONES[owner_bot_id]["client"]
        target_channel = int(RUNNING_CLONES[owner_bot_id]["log_channel"])
    else:
        active_client = bot
        target_channel = int(Config.LOG_CHANNEL)

    try:
        # Wake Up Call
        try: await active_client.get_chat(target_channel)
        except: pass

        # 4. Get Message & Media Object
        msg = await active_client.get_messages(target_channel, int(file_data['message_id']))
        media = msg.document or msg.video or msg.audio
        if not media: raise Exception("Media not found")
        
        # 5. Initialize Streamer (PASS 'media' OBJECT, NOT STRING ID)
        streamer = TgFileStreamer(
            active_client, 
            media,  # <--- THIS IS THE FIX (Passing the object)
            file_data['file_size'], 
            request.headers.get("range")
        )
        
        # 6. Response Headers
        response_size = (streamer.end - streamer.start) + 1
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(response_size),
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"',
        }
        
        status_code = 206 if request.headers.get("range") else 200
        if status_code == 206:
            headers["Content-Range"] = f"bytes {streamer.start}-{streamer.end}/{file_data['file_size']}"

        return StreamingResponse(
            streamer, 
            status_code=status_code, 
            media_type=file_data['mime_type'], 
            headers=headers
        )

    except Exception as e:
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=500, detail="File Stream Failed")
