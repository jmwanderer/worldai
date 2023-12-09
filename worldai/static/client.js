// Active elements in client chat view
const messages = document.getElementById("messages")
const user_input = document.getElementById("user")
const send_button = document.getElementById("send")

function addUserMessage(message) {
    messages.innerHTML +=
        '<p><b>You</b><br>' + message + '</p>';
}

function addAssistantMessage(message) {
    messages.innerHTML +=
        '<p><b>Assistant</b><br>' + message + '</p>';
}

// True if chat message is outstanding
in_progress = false;

// A server side key defining the object in view
current_view = null;

// Does the initial setup of the chat contents and
// the curent object view
const loadAction = async() => {
    in_progress = true;

    // Get the chat history.
    const response = await fetch(url, {
        headers: {
            "Authorization": bearer_token
        }
    });
    const values = await response.json();
    current_view = values['view']
    loadContent(current_view)
    const msg_list = values["messages"];
    if (msg_list.length == 0) {
        // If empty, include  a welcome message
        addAssistantMessage(
            "Hello, welcome to world builder!<br>" +
                "I can help you create worlds filled with main characters, " +
                "special items, and key sites.<br>"+
                "I will ask you for your input, but feel free to ask " +
                "me to come up with the ideas and information.<br>" +
                "Enter your request in the text box below.");
    }
    // Display chat history
    for (i in msg_list) {
        addUserMessage(msg_list[i]["user"]);
        addAssistantMessage(msg_list[i]["assistant"]);
    }
    // Scroll to bottom of chat history
    messages.scrollTop = messages.scrollHeight;
    in_progress = false;
}

// Chat message exchange with server
const postAction = async() => {
    if (in_progress) {
        return
    }
    in_progress = true;
    text = user_input.value;
    user_input.value = 'running...';
    user_input.disabled = true;
    send_button.disbled = true;
    addUserMessage(text);
    messages.scrollTop = messages.scrollHeight;
    
    const response = await fetch(url, {
        method: 'POST',
        body: '{ "user": "' + text + '"}',
        headers: {
            'Content-Type': 'application/json',
            "Authorization": bearer_token            
        }
    });
    const values = await response.json();
    user_input.value = '';
    user_input.disabled = false;
    user_input.focus();
    send_button.disbled = false;
    addAssistantMessage(values["assistant"]);
    in_progress = false;
    messages.scrollTop = messages.scrollHeight;

    // If the view or contents of the object view have changed,
    // reload.
    view = values['view']
    if (view != current_view || values['changes']) {
        current_view = view;
        loadContent(view);
    }
}

// Submit a message when user presses 'enter'
function keyEvent(key) {
    if (key.keyCode == 13) {
        postAction();
        key.preventDefault();
    }
}
user_input.addEventListener("keydown", keyEvent);
send_button.onclick = postAction;

// Send comment to clear contents of current thread
async function clearThread() {
    const response = await fetch(url, {
        method: 'POST',
        body: '{ "command": "clear_thread" }',
        headers: {
            'Content-Type': 'application/json',
            "Authorization": bearer_token                        
        }
    });
    document.location.reload();
}

// Display for the current object view
const content = document.getElementById("content")
image_list = [];

async function loadContent(view) {
    console.log(`load content ${JSON.stringify(view)}`)
    const response = await fetch(url_obj, {
        method: 'POST',
        body: JSON.stringify(view),
        headers: {
            'Content-Type': 'application/json',
            "Authorization": bearer_token                        
        }
    });

    const values = await response.json();
    content.innerHTML = values['html'];
    image_list = values['images'];
    setup_image_handlers();
}

// Active controls for image. Do not exist
// in all object views
let image = null;
let image_back = null;
let image_fwd = null;
let index = 0;

// Callback to change the current image display
// Deleta is +1 or -1 to advance or reverse
function setImageIndex(delta) {
    let new_index = index + delta;
    if (new_index >= 0 && new_index < image_list.length) {
        index = new_index;
        image.src = image_list[index];
    }
    image_back.disabled = (index == 0);
    image_fwd.disabled = (index == image_list.length - 1);
}

// Setup control for image handlers in object
// display if they exist
function setup_image_handlers() {
    image = document.getElementById("image");
    image_back = document.getElementById("image_back");
    image_fwd = document.getElementById("image_fwd");                  
    index = 0;
    
    console.log("check image");                                      
    if (image) {
        console.log("install image handlers");               
        image_back.onclick = () => setImageIndex(-1);
        image_fwd.onclick = () => setImageIndex(1);
        setImageIndex(0);
    }
}
