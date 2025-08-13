const chatBox = document.getElementById('chat-box');

const recordBtn = document.getElementById('record-btn');
const playback = document.getElementById('audio-player');

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let isPlaying = false;

let session_id = new URLSearchParams(window.location.search).get("session_id");
if(!session_id) {
    session_id = Math.random().toString(36).substring(2,10);
    window.history.replaceState({}, "", `?session_id=${session_id}`);
}

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
        const stream = await navigator.mediaDevices.getUserMedia({audio:true});
        
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            if(event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, {type:"audio/webm"});
            
            askLLMWithMurf(audioBlob);
        };

        mediaRecorder.start();
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
    if(mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        recordBtn.textContent = "Start";
        recordBtn.classList.remove('recording');
    }
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