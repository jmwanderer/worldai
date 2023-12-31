import React from 'react';
import { useState } from 'react';
import { useRef } from 'react';
import { useEffect } from 'react';
import './App.css';

import Button from 'react-bootstrap/Button';
import CloseButton from 'react-bootstrap/CloseButton';
import Card from 'react-bootstrap/Card';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Image from 'react-bootstrap/Image';
import Stack from 'react-bootstrap/Stack';

import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';

/*
 * TODO:
 * - get auth token
 * - get a url prefix for fetch
 * - support multiple images
 */

/*global url_pre, auth_key*/
let URL="/"
if (url_pre.substring(0,2) !== "{{") {
    URL=url_pre;
}
console.log("URL Prefix: " + URL);

let AUTH_KEY="auth"
if (auth_key.substring(0,2) !== "{{") {
    AUTH_KEY=auth_key
}
console.log("AUTH Key: " + AUTH_KEY);    



// Shows a single message exchange.
function MessageExchange({ name, message }) {
    let user_message = "";

    if (message.user.length > 0) {
        user_message = (
            <div className="App-message">            
                <b>You:</b> <br/> { message.user }
            </div>);
    }
    return (
        <div>
            { user_message }
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
    }, [content]);
              
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


function ChatScreen({ name, worldId, characterId, onChange}) {
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
            const url = URL + "threads/worlds/" + worldId +
                  "/characters/" + characterId;
            try {
                const response =
                      await fetch(url,
                                  {signal: signal,
                                   headers: {
                                       "Authorization": "Bearer " + AUTH_KEY
                                   }
                                  });
                const values = await response.json();
                setChatHistory(values["messages"]);
                if (values["messages"].length === 0) {
                    setUserInput("hello");
                    submitClick();
                }
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
            const url = URL + "threads/worlds/" + worldId +
                  "/characters/" + characterId;
            // Post the user request
            try {            
                const response = await fetch(url, {
                    method: 'POST',
                    body: JSON.stringify(data),
                    headers: {
                        'Content-Type': 'application/json',
                        "Authorization": "Bearer " + AUTH_KEY
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
            onChange()
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
            <p>
                Have support: { character.givenSupport ? "Yes" : "No" }
            </p>
        </div>
    );
}

function ChatCharacter({ worldId, characterId, setCharacterId}) {
    const [character, setCharacter] = useState(null);
    const [refresh, setRefresh] = useState(null);    
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Load the character
            const url = URL + "worlds/" + worldId +
                  "/characters/" + characterId;
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
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
    }, [worldId, characterId, refresh]);


    function clickClose() {
        setCharacterId(null);
    }

    function handleUpdate() {
        setRefresh(refresh + 1);
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
                                characterId={characterId}
                                onChange={handleUpdate}
                    />
                </td>
            </tr>
        );
    }

    return (
        <div>
            <CloseButton onClick={clickClose}/>
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
        <tr onClick={handleClick}>
            <td className="App-item">
                <img className="App-thumb"
                     src={character.image.url} alt="person"/>
            </td>
            <td className="App-item">
                <div className="App-world-item">                        
                    <u>{ character.name }</u>
                    <br/>
                            { character.description }
                    <br/>
                </div>
            </td>
            <td className="App-item">
                { character.givenSupport ? "Done" : "Not Done" }
            </td>
        </tr>
    );
    
}

function SelectCharacter({ worldId, setCharacterId, setSiteId }) {

    const [characterList, setCharacterList] = useState([]);

    useEffect(() => {
        let ignore = false;

        async function getCharacterData() {
            // Get the status of progress in the world
            const url = URL + "worlds/" + worldId + "/characters";
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
                          }
                      });
                const values = await response.json();
                if (!ignore) {
                    setCharacterList(values);
                }
            } catch {
            }
        }
        
        getCharacterData();
        return () => {
            ignore = true;
        }
    }, [worldId]);

    function selectCharacter(character_id) {
        setCharacterId(character_id);
    }

    function clickClose() {
        setSiteId(null);
    }
    
    const entries = characterList.map(entry =>
        <CharacterItem key={entry.id}
                       character={entry}
                       onClick={selectCharacter}/>
    );

    return (
        <div>
            <CloseButton onClick={clickClose}/>
            <div className="App-world-list">
                <table>
                    <tbody>
                        { entries }
                    </tbody>
                </table>
            </div>
        </div>            
    );
}


function Site({ worldId, siteId, setSiteId }) {
    const [site, setSite] = useState(null);

    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Load the site
            const url = URL + "worlds/" + worldId +
                  "/sites/" + siteId;
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
                          }
                      });
                const value = await response.json();
                if (!ignore) {
                    setSite(value);
                }
            } catch {
            }
        }
        getData();
        return () => {
            ignore = true;
        }
    }, [worldId, siteId]);

    function clickClose() {
        setSiteId(null);
    }

    if (site) {
        return (
            <div className="App-char-screen">
                Name: {site.name}
                <div>
                    <img src={site.images[0].url}
                         alt="site"
                         className="App-img"/>
                </div>
                Notes:<br/>
                <div>
                    {site.description}
                </div>
            </div>);
    } else {
        return <div className="App-char-screen"></div>
    }
}
    


function SiteItem({ site, onClick }) {
    function handleClick() {
        onClick(site.id);
    }
    return (
        <div onClick={handleClick}>
            <Card  className="m-2">
                <Card.Img src={site.image.url} style={{ width: '12rem'}}/>
                <Card.Title>
                    { site.name }
                </Card.Title>
            </Card>
        </div>);
}    

function World({ worldId, setWorldId }) {
    const [world, setWorld] = useState(null);            
    const [siteList, setSiteList] = useState([]);
    const [siteId, setSiteId] = useState(null);

    const [characterId, setCharacterId] = useState(null);
    
    useEffect(() => {
        let ignore = false;

        async function getSiteData() {
            // Get the status of progress in the world
            const url = URL + "worlds/" + worldId + "/sites";
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
                          }
                      });
                const values = await response.json();
                if (!ignore) {
                    setSiteList(values);
                }
            } catch {
            }
        }

        async function getWorldData() {
            // Get the status of progress in the world
            const url = URL + "worlds/" + worldId;
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
                          }
                      });
                const values = await response.json();
                if (!ignore) {
                    setWorld(values);
                }
            } catch {
            }
        }
        
        getSiteData();
        getWorldData();        
        return () => {
            ignore = true;
        }
    }, [worldId]);

    function clickClose() {
        setWorldId("");
    }

    function selectSite(site_id) {
        setSiteId(site_id);
    }

    if (world === null || siteList === null) {
        return (<div></div>);
    }

    let screen = ""
    if (!siteId) {
        // Show sites
        const rows = []
        for (let row = 0; row < siteList.length / 3; row++) {
            let cols = []
            for (let col = 0; col < 3; col++) {
                let index = row * 3 + col;
                if (index < siteList.length) {
                    cols.push(<Col>
                                  <SiteItem key={siteList[index].id}
                                            site={siteList[index]}
                                            onClick={selectSite}/>
                              </Col>)
                } else {
                    cols.push(<Col></Col>)
                }
            }
            rows.push(<Row>  { cols } </Row>)
        }
        screen = <Container>
                     { rows }
                 </Container>                     
    } else {
        screen = <Site worldId={worldId}
                       siteId={siteId}
                       setSiteId={setSiteId}/>
    }

/*    
        if (!characterId) {
        screen = <SelectCharacter worldId={worldId}
                                  setCharacterId={setCharacterId}
                                  setSiteId={setSiteId}/>
    } else {
        screen = <ChatCharacter worldId={worldId}
                                characterId={characterId}
                                setCharacterId={setCharacterId}/>
                                }
*/
    
    

    return (
        <div>
            <h2>
                World: {world.name}
            </h2>
            <Navbar expand="lg" className="bg-body-tertiary">
                <Container>
                    <CloseButton onClick={clickClose}/>
                    <Nav>
                        <Nav.Link>Inventory</Nav.Link>
                        <Nav.Link>Characters</Nav.Link>
                        <Nav.Link>Items</Nav.Link>                        
                    </Nav>
                </Container>
            </Navbar>
            { screen }
        </div>            
    );
}


function WorldItem({ world, onClick }) {

    function handleClick() {
        onClick(world.id);
    }
    
    return (
        <div class="card mb-3" onClick={handleClick} >
            <div class="row no gutters">
                <div class="col-md-2">
                    <img src={world.image.url} class="card-img" alt="world"/>
                </div>
                <div class="col-md-8">
                    <div class="card-body">
                        <h5 class="card-title">
                            { world.name }
                        </h5>
                        <p class="card-text" style={{ textAlign: "left" }}>
                            { world.description }
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

function SelectWorld({setWorldId}) {
    const [worldList, setWorldList] = useState([]);
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Get the list of worlds
            const url = URL + "worlds";
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
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
        <Stack gap={3}>
            { entries }
        </Stack>
    );
}
    
    
function App() {
    const [worldId, setWorldId] = useState(null);
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Get initial load data
            const url = URL + "initdata";
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
                          }
                      });
                const values = await response.json();
                if (!ignore) {
                    setWorldId(values['world_id']);
                }
            } catch {
            }
        }
        
        getData();
        return () => {
            ignore = true;
        }
    }, []);
    console.log("App: " + worldId)

    let screen = ""
    if (worldId === null) {
        screen = <p>Loading...</p>
    } else if (worldId === "") {
        screen = <SelectWorld setWorldId={setWorldId}/>
    } else {
        screen = <World worldId={worldId}
                        setWorldId={setWorldId}/>
    }        
    return (
        <div className="App">
            <header className="App-header">
                { screen }
            </header>
        </div>
    );
}

function AxApp() {
    return (
        <div className="App">
            <header className="App-header">
                <div className='alert alert-primary' role='alert'>
                    <p style={{display:"none"}} className='d-block'>
                        Bootstrap is installed
                    </p>
                    <p className='d-none'>
                        Bootstrap not installed
                    </p>
                </div>
            </header>
        </div>
    );
}
export default App;
