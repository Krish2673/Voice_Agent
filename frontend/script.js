const Generate_btn = document.getElementById('generate_btn')

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
})