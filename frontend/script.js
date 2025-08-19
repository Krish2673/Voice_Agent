const chatBox = document.getElementById('chat-box');
const recordBtn = document.getElementById('record-btn');
const playback = document.getElementById('audio-player');

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let isPlaying = false;
let audioContext, source, processor, stream;

let session_id = new URLSearchParams(window.location.search).get("session_id");
if(!session_id) {
    session_id = Math.random().toString(36).substring(2,10);
    window.history.replaceState({}, "", `?session_id=${session_id}`);
}

let partialDiv = null;
let socket;

function initSocket() {
    socket = new WebSocket(`ws://${window.location.host}/agent/chat/${session_id}`);

    socket.onopen = () => {
        console.log("Websocket Connected!");
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if(data.type === "error") {
                appendMsg("LLM",data.error || "Something went Wrong");
                recordBtn.disabled = false;
                recordBtn.textContent = "Start";
                return;
            }

            if(data.type === "partial_transcript") {
                if(!partialDiv) {
                    partialDiv = document.createElement('div');
                    partialDiv.className = "message user-msg partial";
                    partialDiv.innerHTML = `<strong>You : </strong> ${data.text || "(Listening...)"}`;
                    chatBox.appendChild(partialDiv);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                else {
                    partialDiv.innerHTML = `<strong>You : </strong> ${data.text}`;
                }
            }

            if(data.type === "final_transcript") {
                if(partialDiv) {
                    partialDiv.innerHTML = `<strong>You : </strong> ${data.text}`;
                    partialDiv.classList.remove("partial");
                    partialDiv = null;
                }
                else {
                    appendMsg("You", data.text || "(No Transcript)");
                }
            }

            if(data.type === "turn_end") {
                console.log("User turn ended.");
                stopRecording();
            }

            if(data.type === "response") {
                appendMsg("LLM", data.llm_text || "(No response)");
            }

            if(data.type === "audio" && data.audio_url) {
                isPlaying = true;
                playback.src = data.audio_url;
                playback.load();
                playback.play();

                playback.onended = () => {
                    isPlaying = false;
                    recordBtn.disabled = false;
                    recordBtn.classList.remove('thinking');
                    recordBtn.textContent = "Start";
                    startRecording();
                };
            }
        }

        catch(err) {
            console.error("Invalid ws message: ", event.data);
        }
    };

    socket.onclose = () => {
        console.log("Websocket closed, reconnecting...");
        setTimeout(initSocket,2000);
    };

    socket.onerror = (err) => {
        console.error("Websocket error: ", err);
    };
}

initSocket();

function appendMsg(sender,text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender === "You" ? "user-msg" : "bot-msg"}`;
    msgDiv.innerHTML = `<strong>${sender} : </strong> ${text}`
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    // return msgDiv;
}

recordBtn.addEventListener('click', () => {
    if(isPlaying) return;
    if(!isRecording) startRecording();
    else stopRecording();
});

async function startRecording() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext = new AudioContext({ sampleRate: 16000 }); // force 16kHz
        source = audioContext.createMediaStreamSource(stream);

        // create a processor to grab raw audio
        processor = audioContext.createScriptProcessor(4096, 1, 1);
        source.connect(processor);
        processor.connect(audioContext.destination);

        processor.onaudioprocess = (event) => {
            const inputData = event.inputBuffer.getChannelData(0); // Float32
            const pcm16 = floatTo16BitPCM(inputData);
            const blob = new Blob([pcm16], { type: "application/octet-stream" });
            socket.send(blob); // send raw PCM16 to backend
        };

        // mediaRecorder.start(500);
        isRecording = true;
        recordBtn.textContent = "Stop";
        recordBtn.classList.add('recording');        
    }
    catch (error){
        console.error("Microphone error ocurred:", error);
        alert("Microphone access is required!");
    }
}

function stopRecording() {
    if (!isRecording) return;

    if (processor) {
        processor.disconnect();
        processor.onaudioprocess = null;
    }
    if (source) source.disconnect();
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    if (audioContext) audioContext.close();

    // tell backend recording is finished
    socket.send(JSON.stringify({ type: "end_of_audio" }));

    isRecording = false;
    recordBtn.textContent = "Start";
    recordBtn.classList.remove('recording');
}

let convoHistory = []

async function askLLMWithMurf(blob) {
    recordBtn.disabled = true;
    recordBtn.textContent = "Thinking...";
    recordBtn.classList.add('thinking');

    try {
        const formData = new FormData();
        formData.append("file",blob,"recording.wav");

        const response = await fetch(`/agent/chat/${session_id}`, {
            method : "POST",
            body : formData
        });
        
        if(response.status === 204) {
            appendMsg("LLM","...No speech detected.")
            return;
        }

        const data = await response.json();

        if(!response.ok) {
            appendMsg("LLM",data.error || "Something Went Wrong");
            return;
        }

        if(data.audio_url) {
                isPlaying = true;
                playback.src = data.audio_url;
                playback.load();
                playback.play();
                recordBtn.classList.remove('thinking');
                recordBtn.textContent = "Start";
        }
        else {
            recordBtn.disabled = false;
            recordBtn.textContent = "Start";
        }

        appendMsg("You",data.user_transcript || "(No Transcript)");
        appendMsg("LLM",data.llm_text || "(No response)");

        playback.onended = () => {
            isPlaying = false;
            recordBtn.disabled = false;
            recordBtn.classList.remove('thinking');
            recordBtn.textContent = "Start";
            startRecording();
        }
    }

    catch(err) {
        console.error(err);
        appendMsg("LLM",`❌ Error: ${err.message}`)
        recordBtn.disabled = false;
        recordBtn.textContent = "Start"
    }

    finally {
        recordBtn.classList.remove('thinking');
    }
}

function floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, float32Array[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return buffer;
}