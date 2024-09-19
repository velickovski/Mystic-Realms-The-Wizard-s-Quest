document.addEventListener('DOMContentLoaded', function() {
    let storyText = '';

    document.getElementById('start-btn').addEventListener('click', () => {
        document.getElementById('start-btn').style.display = 'none';
        fetch('/start_game', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                getWizardStatus();
                getStory();
            });
    });

    function getWizardStatus() {
        fetch('/get_wizard_status')
            .then(response => response.json())
            .then(data => {
                if (data.name && data.health !== undefined) {
                    document.getElementById('wizard-name').innerText = data.name;
                    updateHealthBar(data.health);
                    document.getElementById('wizard-status').style.display = 'block';
                }
            });
    }

    function updateHealthBar(health) {
        const healthBar = document.getElementById('health-bar');
        const healthPercentage = Math.max(0, Math.min(health, 100)); // Clamp between 0 and 100
        healthBar.style.width = `${healthPercentage}%`;

        // Change color based on health percentage
        if (healthPercentage > 60) {
            healthBar.style.backgroundColor = '#4caf50'; // Green
        } else if (healthPercentage > 30) {
            healthBar.style.backgroundColor = '#ff9800'; // Orange
        } else {
            healthBar.style.backgroundColor = '#f44336'; // Red
        }
    }

    function getStory(choice = -1) {
        document.getElementById('story-content').innerText = '';
        document.getElementById('choices').innerHTML = '';
        document.getElementById('loading').innerText = 'Loading story...';
        storyText = '';

        fetch('/get_story', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `choice=${choice}`
        })
        .then(response => {
            const reader = response.body
                .pipeThrough(new TextDecoderStream())
                .getReader();

            function readChunk() {
                return reader.read().then(({ value, done }) => {
                    if (done) {
                        document.getElementById('loading').innerText = '';
                        // Start typing effect after all text is received
                        typeEffect(storyText, () => {
                            // Callback after typing effect is done
                            getChoices();
                            getWizardStatus(); // Refresh wizard status
                        });
                        return;
                    }
                    if (value) {
                        storyText += value;
                    }
                    return readChunk();
                });
            }
            return readChunk();
        });
    }

    let typing = false;
    let typingQueue = [];

    function typeEffect(text, callback) {
        typingQueue = [...text];
        typing = true;
        const storyDiv = document.getElementById('story-content');
        storyDiv.innerHTML = ''; 
        function typingAnimation() {
            if (typingQueue.length > 0) {
                const char = typingQueue.shift();
                if (char === '\n') {
                    storyDiv.innerHTML += '<br>';
                } else {
                    storyDiv.innerHTML += char;
                }
                setTimeout(typingAnimation, 30); // Adjust typing speed here
            } else {
                typing = false;
                if (callback) {
                    callback();
                }
            }
        }
        typingAnimation();
    }

    function getChoices() {
        fetch('/get_choices')
            .then(response => response.json())
            .then(data => {
                const choicesDiv = document.getElementById('choices');
                choicesDiv.innerHTML = '';
                data.choices.forEach((choiceText, index) => {
                    const btn = document.createElement('button');
                    btn.innerText = choiceText;
                    btn.className = 'choice-btn';
                    btn.addEventListener('click', () => {
                        storyText = '';
                        getStory(index);
                    });
                    choicesDiv.appendChild(btn);
                });
            })
            .catch(error => {
                console.error('Error fetching choices:', error);
            });
    }
});
