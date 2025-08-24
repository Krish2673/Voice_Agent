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
let llmDiv = null;
let llmBuffer = "";
let socket;
let audioQueue = [];
let isPlayingStream = false;
let audioCtx = new (window.AudioContext || window.webkitAudioContext)();
let firstChunk = true;

function initSocket() {
    socket = new WebSocket(`ws://${window.location.host}/agent/chat/${session_id}`);

    socket.onopen = () => {
        console.log("Websocket Connected!");
    };

    socket.onmessage = (event) => {
        try {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch {
                data = null;
            }

            if(data && data.type) {
                if(data.type === "error") {
                appendMsg("LLM",data.error || "Something went Wrong");
                recordBtn.disabled = false;
                recordBtn.textContent = "Start";
                return;
                }

                if (data.type === "audio_chunk") {
                    const wavData = base64ToArrayBuffer(data.data);
                    const pcmData = firstChunk ? wavData.slice(44) : wavData;
                    firstChunk = false;
                    audioQueue.push(pcmData);
                    if (!isPlayingStream) {
                        playNextChunk();
                    }
                }
                else if (data.type === "end_of_audio") {
                    console.log("[Client] Audio stream completed");
                    firstChunk = true;
                    startRecording();
                }

                else if (data.type === "llm_chunk") {
                    llmBuffer += data.text;
                }

                else if (data.type === "llm_end") {
                    if(!llmDiv) {
                        llmDiv = document.createElement('div');
                        llmDiv.className = "message bot-msg";
                        chatBox.appendChild(llmDiv);
                    }
                    llmDiv.innerHTML = `<strong>LLM : </strong> ${llmBuffer}`;
                    chatBox.scrollTop = chatBox.scrollHeight;

                    console.log("[Client] LLM response completed.");
                    llmDiv = null;
                    llmBuffer = "";
                }

                else if(data.type === "partial_transcript") {
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

                else if(data.type === "final_transcript") {
                    if(partialDiv) {
                        partialDiv.innerHTML = `<strong>You : </strong> ${data.text}`;
                        partialDiv.classList.remove("partial");
                        partialDiv = null;
                    }
                    else {
                        appendMsg("You", data.text || "(No Transcript)");
                    }
                }

                else if(data.type === "turn_end") {
                    console.log("User turn ended.");
                    stopRecording();
                }
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

window.onload = () => {
    initSocket();
};

function appendMsg(sender,text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender === "You" ? "user-msg" : "bot-msg"}`;
    msgDiv.innerHTML = `<strong>${sender} : </strong> ${text}`
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

recordBtn.addEventListener('click', () => {
    if(isPlaying) return;
    if(!isRecording) startRecording();
    else stopRecording();
});

async function startRecording() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: {
                channelCount : 1,
                sampleRate : 16000,
                noiseSuppression :true,
                echoCancellation : true,
                autoGainControl : true
            } 
        });
        audioContext = new AudioContext({ sampleRate: 16000 });
        source = audioContext.createMediaStreamSource(stream);

        processor = audioContext.createScriptProcessor(4096, 1, 1);
        const silentNode = audioContext.createGain();
        silentNode.gain.value = 0;

        source.connect(processor);
        processor.connect(silentNode);
        silentNode.connect(audioContext.destination);

        processor.onaudioprocess = (event) => {
            const inputData = event.inputBuffer.getChannelData(0); 
            const pcm16 = floatTo16BitPCM(inputData);
            const blob = new Blob([pcm16], { type: "application/octet-stream" });
            socket.send(blob);
            console.log("[Client] Sent audio chunk");
        };

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

function playNextChunk() {
    if (audioQueue.length === 0) {
        isPlayingStream = false;
        return;
    }

    isPlayingStream = true;
    const chunk = audioQueue.shift();

    // convert PCM16 → Float32
    const float32 = pcm16ToFloat32(new DataView(chunk));

    // create AudioBuffer
    const audioBuffer = audioCtx.createBuffer(1, float32.length, audioCtx.sampleRate);
    audioBuffer.getChannelData(0).set(float32);

    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);

    source.onended = () => {
        playNextChunk(); // chain next chunk
    };

    source.start(0);
}

function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

function pcm16ToFloat32(dataView) {
    const len = dataView.byteLength / 2;
    const result = new Float32Array(len);
    for (let i = 0; i < len; i++) {
        const s = dataView.getInt16(i * 2, true);
        result[i] = s / 0x8000;
    }
    return result;
}