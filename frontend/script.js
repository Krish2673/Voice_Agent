const Generate_btn = document.getElementById('generate_btn');

const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const playback = document.getElementById('echoPlayer');
const resetBtn = document.getElementById('reset-btn');

const statusDiv = document.getElementById('status');

Generate_btn.addEventListener('click', async (e) => {
    e.preventDefault();
    const textIP = document.getElementById('ip_text').value;

    if(!textIP.trim()) {
        alert("Please Enter some Text!")
        return;
    }

    try {
        const response = await fetch("/generate-audio", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                text : textIP,
                voice_id : "en-US-terrell"
            })
        });

        if(!response.ok)
            throw new Error("Failed to Generate Audio!")

        const data = await response.json();
        console.log("Fetched response:", data);
        
        const audioUrl = data.audio_url;
        console.log("Audio URL:", audioUrl);
        
        const audioPlayer = document.getElementById("audioPlayer");
        audioPlayer.src = audioUrl;
        audioPlayer.style.display = "block";
        audioPlayer.load();
        audioPlayer.play();
    }

    catch(error) {
        console.error("Error: ", error);
        alert("Something went wrong. Please try again!")
    }
});

let mediaRecorder;
let audioChunks = [];

startBtn.addEventListener('click', async() => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({audio:true});
        
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        document.getElementById('record-indicator').style.display = 'block';

        mediaRecorder.ondataavailable = event => {
            if(event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, {type:"audio/webm"});
            const audioUrl = URL.createObjectURL(audioBlob);

            playback.src = audioUrl;
            // playback.style.display = "block";

            resetBtn.disabled = false;
            resetBtn.style.cursor = "pointer";

            document.getElementById('record-indicator').style.display = 'none';
            
            uploadAudio(audioBlob);
        };

        mediaRecorder.start();

        startBtn.disabled = true;
        stopBtn.disabled = false;
        stopBtn.style.cursor = "pointer";
    }
    catch (error){
        console.error("Microphone access denied or error ocurred:", error);
        alert("Microphone access is required to use Echo Bot!");
    }
});

stopBtn.addEventListener('click', () => {
    if(mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
});

resetBtn.addEventListener('click', () => {
    audioChunks = [];
    playback.src = "";
    playback.style.display = "none";
    resetBtn.disabled = true;
    resetBtn.style.cursor = "not-allowed";
    document.getElementById('record-indicator').style.display = 'none';
    stopBtn.disabled = true;
    stopBtn.style.cursor = "not-allowed";
    statusDiv.innerHTML = "";
    statusDiv.style.display = "none";
});

async function uploadAudio(blob) {
    statusDiv.textContent = "Uploading...";

    const formData = new FormData();
    formData.append("file",blob,"recording.wav");

    try {
        const response = await fetch("/upload-audio", {
            method : "POST",
            body : formData
        })

        if(!response.ok) {
            throw new Error(`Upload Failed: ${response.status}`);
        }

        const result = await response.json();

        statusDiv.style.display = "block";
        statusDiv.innerHTML = `
        ✅ Upload successful <br>
        Name : ${result.filename} <br>
        Type : ${result.content_type} <br>
        Size : ${result.size_kb} KB`;
    }
    catch(error) {
        statusDiv.textContent = `❌ Upload failed: " ${error.message}`;
    }
}