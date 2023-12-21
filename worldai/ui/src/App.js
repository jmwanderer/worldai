import elysia from './elysia.png';
import './App.css';
import { useState } from 'react';
import { useRef } from 'react';
import { useEffect } from 'react';


const character = {
    id: "id404bc8b4",
    name: "Elysia",
    description: "A skilled archer with a mysterious past, on a personal quest to find a legendary artifact that has the power to restore balance to the world.",
    image: elysia
}


// Simple button. May change in the future.
function Button({ text, onClick, disabled }) {
    return (
            <button disabled={disabled} onClick={onClick}>
            { text }
        </button>
    );
}

// Shows a single message exchange.
function MessageExchange({ name, message }) {
    return (
            <div>
            <div className="App-message">
                  <b>You:</b> <br/> { message.user } </div>
            <div className="App-message">
            <b> {name}: </b> <br/> { message.reply} </div>
            </div>
    );
}

function CurrentMessage({ content, chatState}) {
    const divRef = useRef();
    useEffect(() => {
        const {current} = divRef;
        if (current !== null) {
            current.scrollIntoView({behavior: "smooth"});
        }
    });
              
    let user = "";
    if (content.user.length > 0) {
         user = <div> User: {content.user} </div>;
    }
    let running = "";
    if (chatState !== "ready") {
        running = <div className="App-running"><i> Running... </i></div>
    }
    let error = "";
    if (content.error.length > 0) {
        error = <div> Error: { content.error } </div>;
    }
    return (
            <div ref={divRef}>
            { user }
        { running}
        { error }
        </div>
    );
}

function MessageScreen({chatHistory, currentMessage, chatState}) {
    const entries = chatHistory.map(entry =>
            <MessageExchange key={entry.id} message={entry} name="Elysia"/>
    );

    return (
            <div className="App-message-screen">
            { entries }
            <CurrentMessage content={currentMessage}
                            chatState={chatState}/>
            </div>
    );
}

function UserInput({value, onChange, onKeyDown, disabled}) {
    return (
            <textarea
        value={value} className="App-user-input"
        disabled={disabled}
        onChange={onChange} onKeyDown={onKeyDown}/>
    );
}


function ChatScreen() {
    const [chatHistory, setChatHistory] = useState([]);
    const [currentMessage,
           setCurrentMessage] = useState({ user: "", error: ""});
    const [userInput, setUserInput] = useState("")
    const [chatState, setChatState] = useState("ready")
    
    useEffect(() => {
        const controller = new AbortController();
        const signal = controller.signal;
        async function getData() {
            // Get the chat history.        
            const url = "/threads/123";
            try {
                const response =
                      await fetch(url, {signal: signal,
                                        headers: {
                                            "Authorization": "Bearer auth"
                                        }
                                       });
                const values = await response.json();
                console.log(values)
                setChatHistory(values["messages"]);
            } catch {
            }
        }
        getData();
        return () => {
            controller.abort();
        }
    }, []);
    

    function submitClick() {
        let user_msg = userInput
        setCurrentMessage({user: user_msg, error: ""});
        setUserInput("");
        setChatState("waiting");

        async function getData() {
            const data = { "user": user_msg }
            const url = "/threads/123";
            // Post the user request
            try {            
                const response = await fetch(url, {
                    method: 'POST',
                    body: JSON.stringify(data),
                    headers: {
                        'Content-Type': 'application/json',
                        "Authorization": "Bearer auth"
                    }
                });
                const values = await response.json();
                console.log(values)
                setChatHistory([...chatHistory, values])
                setCurrentMessage({user: "", error: "" });
            } catch (e) {
                setCurrentMessage({user: user_msg,
                                   error: "Something went wrong."});
            }
            setChatState("ready")
        }
        getData();
    }

    function clearClick() {
        setChatHistory([]);
    }

    function handleInputChange(e) {
        setUserInput(e.target.value);
    }

    function handleKeyDown(e) {
        if (chatState == "ready") {
            if (e.keyCode === 13) {
                submitClick();
                e.preventDefault();            
            }
        }
    }

    let disabled = (chatState !== "ready");
    return (
            <div className="App-chat-screen">
            <MessageScreen chatHistory={chatHistory}
        currentMessage={currentMessage}
        chatState={chatState}
            />
            <div>
            <UserInput value={userInput} onChange={handleInputChange} onKeyDown={handleKeyDown}/>
            </div>
            <Button disabled={disabled} onClick={clearClick} text="Clear Thread"/>
            <Button disabled={disabled} onClick={submitClick} text="Submit"/>      
            </div>
    );
}

function CharacterScreen() {
    return (
            <div className="App-char-screen">
            Name: {character.name}
            <div>
            <img src={character.image} alt="person" className="App-img"/>
            </div>
            Notes:<br/>
            <div>
            {character.description}
        </div>
            </div>
    );
}


function App() {
    
    return (
            <div className="App">
            <header className="App-header">

            <table className="App-table">
            <tbody className="App-tbody">
            <tr>
            <td className="App-td">
            <CharacterScreen/>
            </td>
            <td className="App-td">
            <ChatScreen/>
            </td>
            </tr>
            </tbody>
            </table>
            </header>
            </div>
    );
}

export default App;
