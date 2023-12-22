import React from 'react';
import { useState } from 'react';
import { useRef } from 'react';
import { useEffect } from 'react';
import './App.css';
import back_image from './back.png';

/*
 * TODO:
 * - support multiple images
 */

/*
 

  
const character = {
    id: "id404bc8b4",
    name: "Elysia",
    description: "A skilled archer with a mysterious past, on a personal quest to find a legendary artifact that has the power to restore balance to the world.",
    image: elysia
}
*/

// Simple button. May change in the future.
function Button({ text, onClick, disabled }) {
    return (
        <button disabled={disabled} onClick={onClick}>
            { text }
        </button>
    );
}

function BackArrow({ onClick }) {
    return (
        <img src={back_image} alt="back"
             onClick={onClick}
             className="App-back-arrow"/>
    );
}

// Shows a single message exchange.
function MessageExchange({ name, message }) {
    return (
        <div>
            <div className="App-message">
                <b>You:</b> <br/> { message.user }
            </div>
            <div className="App-message">
                <b> {name}: </b>
                <br/>
                { message.reply}
            </div>
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

function MessageScreen({chatHistory, currentMessage, chatState, name}) {
    const entries = chatHistory.map(entry =>
        <MessageExchange key={entry.id} message={entry} name={name}/>
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


function ChatScreen({ name, worldId, characterId }) {
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
            const url = "/threads/worlds/" + worldId +
                  "/characters/" + characterId;
            try {
                const response =
                      await fetch(url, {signal: signal,
                                        headers: {
                                            "Authorization": "Bearer auth"
                                        }
                                       });
                const values = await response.json();
                setChatHistory(values["messages"]);
            } catch {
            }
        }
        getData();
        return () => {
            controller.abort();
        }
    }, [worldId, characterId]);
    

    function submitClick() {
        let user_msg = userInput
        setCurrentMessage({user: user_msg, error: ""});
        setUserInput("");
        setChatState("waiting");

        async function getData() {
            const data = { "user": user_msg }
            const url = "/threads/worlds/" + worldId +
                  "/characters/" + characterId;
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
        if (chatState === "ready") {
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
                           name={name}/>
            <div>
                <UserInput value={userInput}
                           onChange={handleInputChange}
                           onKeyDown={handleKeyDown}/>
            </div>
            <Button disabled={disabled}
                    onClick={clearClick}
                    text="Clear Thread"/>
            <Button disabled={disabled}
                    onClick={submitClick}
                    text="Submit"/>      
        </div>
    );
}


function CharacterScreen({ character }) {
    // TODO: support zero images.
    return (
        <div className="App-char-screen">
            Name: {character.name}
            <div>
                <img src={character.images[0].url}
                     alt="person"
                     className="App-img"/>
            </div>
            Notes:<br/>
            <div>
                {character.description}
            </div>
        </div>
    );
}

function ChatCharacter({ worldId, characterId, setCharacterId}) {
    const [character, setCharacter] = useState(null);
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Load the character
            const url = "/worlds/" + worldId +
                  "/characters/" + characterId;
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer auth"
                          }
                      });
                const value = await response.json();
                if (!ignore) {
                    setCharacter(value);
                }
            } catch {
            }
        }
        getData();
        return () => {
            ignore = true;
        }
    }, [worldId, characterId]);


    function clickBack() {
        setCharacterId(null);
    }

    let screen = (<tr/>);
    if (character) {
        screen = (
            <tr>            
                <td className="App-td">
                    <CharacterScreen character={character}/>
                </td>
                <td className="App-td">
                    <ChatScreen name={character.name}
                                worldId={worldId}
                                characterId={characterId}/>
                </td>
            </tr>
        );
    }

    return (
        <div>
            <BackArrow onClick={clickBack}/>
            <table className="App-table">
                <tbody className="App-tbody">{screen}</tbody>
            </table>
        </div>
    );
}


function CharacterItem({ character, onClick }) {

    function handleClick() {
        onClick(character.id);
    }

    return (
        <table>
            <tbody>
                <tr onClick={handleClick}>
                    <td>
                        <img src={character.image.url} alt="person"
                             style={{"maxWidth":"100px"}}/>
                    </td>
                    <td>
                        <div className="App-world-item">                        
                            <u>{ character.name }</u>
                            <br/>
                            { character.description }
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    );
    
}

function SelectCharacter({ worldId, setCharacterId, setWorldId }) {

    const [characterList, setCharacterList] = useState([]);
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Get the list of worlds
            const url = "/worlds/" + worldId + "/characters";
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer auth"
                          }
                      });
                const values = await response.json();
                if (!ignore) {
                    setCharacterList(values);
                }
            } catch {
            }
        }
        getData();
        return () => {
            ignore = true;
        }
    }, [worldId]);

    function selectCharacter(character_id) {
        setCharacterId(character_id);
    }

    function clickBack() {
        setWorldId(null);
    }
    
    const entries = characterList.map(entry =>
        <CharacterItem key={entry.id}
                       character={entry}
                       onClick={selectCharacter}/>
    );

    return (
        <div>
            <BackArrow onClick={clickBack}/>                        
            <div className="App-world-list">
                { entries }
            </div>
        </div>            
    );
}


function WorldItem({ world, onClick }) {

    function handleClick() {
        onClick(world.id);
    }
    
    return (
        <table>
            <tbody>
                <tr onClick={handleClick}>
                    <td>
                        <img src={world.image.url} alt="world"
                             style={{"maxWidth":"100px"}}/>
                    </td>
                    <td>
                        <div className="App-world-item">
                            <u>{ world.name }</u>
                            <br/>
                            { world.description }
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    );
}

function SelectWorld({setWorldId}) {
    const [worldList, setWorldList] = useState([]);
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Get the list of worlds
            const url = "/worlds";
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer auth"
                          }
                      });
                const values = await response.json();
                if (!ignore) {
                    setWorldList(values);
                }
            } catch {
            }
        }
        getData();
        return () => {
            ignore = true;
        }
    }, []);

    function selectWorld(world_id) {
        setWorldId(world_id);
    }
    
    const entries = worldList.map(entry =>
        <WorldItem key={entry.id} world={entry} onClick={selectWorld}/>
    );

    return (
        <div className="App-world-list">
            { entries }
        </div>
    );
}
    
    
function App() {
    const [worldId, setWorldId] = useState(null);
    const [characterId, setCharacterId] = useState(null);

    let screen = ""
    if (!worldId) {
        screen = <SelectWorld setWorldId={setWorldId}/>
    } else if (!characterId) {
        screen = <SelectCharacter worldId={worldId}
                                  setCharacterId={setCharacterId}
                                  setWorldId={setWorldId}/>
    } else {
        screen = <ChatCharacter worldId={worldId}
                                characterId={characterId}
                                setCharacterId={setCharacterId}/>
    }
                         
    return (
        <div className="App">
            <header className="App-header">
                { screen }
            </header>
        </div>
    );
}

export default App;
