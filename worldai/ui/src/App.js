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
import Carousel from 'react-bootstrap/Carousel';

import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';


function extract_prefix(url) {
  // https://localhost:3000/  --> https://localhost:3000
  // https://localhost:3000/ui/play --> https://localhost:3000
  // https://localhost:3000/worldai/ui/play --> https://localhost:3000/worldai

  // Find 3rd / character
  let i = url.indexOf('/')
  i = url.indexOf('/', i + 1)
  i = url.indexOf('/', i + 1)

  // Find 2nd to last / character
  let end = url.lastIndexOf('/')
  end = url.lastIndexOf('/', end - 1)

  if (end < i) {
    end = url.length - 1;
  } 
  return url.substr(0, end);
}

// global URL, auth_key
let URL= extract_prefix(document.location.href);
console.log("URL Prefix: " + URL);

// get from global variable set in index.html
// Following comment is required for compile.
/* global auth_key */
let AUTH_KEY="auth"
if (auth_key.substring(0,2) !== "{{") {
    AUTH_KEY=auth_key
}
console.log("AUTH Key: " + AUTH_KEY);


// Shows a single message exchange.
function MessageExchange({ name, message }) {
    let user_message = "";
    let updates_message = "";    

    if (message.user.length > 0) {
        user_message = (
            <div className="App-message">            
                <b>You:</b> <br/> { message.user }
            </div>);
    }
    if (message.updates && message.updates.length > 0) {
        updates_message = (
            <div className="App-message">            
                <i>{ message.updates }</i>
            </div>);
    }
    return (
        <div className="p-2">
            { user_message }
            <div className="App-message">
                <b> {name}: </b>
                <br/>
                { message.reply}
            </div>
            { updates_message }
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
        <div className="p-2" ref={divRef}>
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
        <Stack className="border m-2" style={{ textAlign: "left",
                                               overflow: "auto"}}>
            
            { entries }
            <CurrentMessage content={currentMessage}
                            chatState={chatState}/>
        </Stack>
    );
}

function UserInput({value, onChange, onKeyDown, disabled}) {
    return (
        <textarea className="m-2"
            value={value} 
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
            const url = URL + "/threads/worlds/" + worldId +
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
                    // TODO: figure out the right way to do this
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
            const url = URL + "/threads/worlds/" + worldId +
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
        <Stack style={{ height: "100%", maxHeight: "90vh" }}>
            <MessageScreen chatHistory={chatHistory}
                           currentMessage={currentMessage}
                           chatState={chatState}
                           name={name}/>
            <UserInput value={userInput}
                       onChange={handleInputChange}
                       onKeyDown={handleKeyDown}/>
            <div>
                <Button disabled={disabled}
                        onClick={submitClick}
                        text="Submit">
                    Submit
                </Button>
            </div>
        </Stack>
    );
}


function CharacterImages({character}) {
    const items = character.images.map(entry =>
        <Carousel.Item key={entry.url}>
            <Image src={entry.url}
                   style={{ maxWidth: "50vmin", maxHeight: "50vmin",
                            minHeight: "30vmin"}}/>                            
        </Carousel.Item>);
            
    return (
        <Carousel interval={null} style={{ textAlign: "center" }}>
            { items }
        </Carousel>            
    );
}


function CharacterScreen({ character }) {
    return (
        <Stack style={{ textAlign: "left" }}>
            <h3>{character.name}</h3>
            <CharacterImages character={character}/>
            <h4>Notes:</h4>
            <h5>{character.description}</h5>
            <p>
                Have support: { character.givenSupport ? "Yes" : "No" }
            </p>
        </Stack>
    );
}

function ChatCharacter({ worldId, characterId, onClose}) {
    const [character, setCharacter] = useState(null);
    const [refresh, setRefresh] = useState(null);    
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Load the character
            const url = URL + "/worlds/" + worldId +
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


    function handleUpdate() {
        setRefresh(refresh + 1);
    }

    if (!character) {
        return <div/>
    }

    return (
        <Container>
            <Row>
                <Col>
                    <CloseBar onClose={onClose}/>
                </Col>
            </Row>
            <Row>
                <Col xs={6}>
                    <CharacterScreen character={character}/>
                </Col>
                <Col xs={6}>
                    <ChatScreen name={character.name}
                                worldId={worldId}
                                characterId={characterId}
                                onChange={handleUpdate}/>
                </Col>
            </Row>
        </Container>
        );
}



function CharacterItem({ character, onClick }) {
    function handleClick() {
        onClick(character.id);
    }
    return (
        <div onClick={handleClick} className="mt-2" style={{ height: "100%"}}>
            <Card style={{ height: "100%"}}>
                <Card.Img src={character.image.url}/>
                  
                <Card.Title>
                    {character.name }
                </Card.Title>
            </Card>
        </div>);
}

function SitePeople({ site, setCharacterId}) {

    const people = site.characters.map(entry =>
        <Col key={entry.id} md={2}>
            <CharacterItem key={entry.id}
                           character={entry}
                           onClick={setCharacterId}/>
        </Col>
    );
    
    return ( <Container className="mt-2">
                 <Row>                 
                     { people }
                 </Row>
             </Container>
           );
}

function ItemCard({ item, onClick }) {
    function handleClick() {
        if (onClick) {
            onClick(item.id);
        }
    }
    return (
        <div onClick={handleClick} className="mt-2" style={{ height: "100%"}}>
            <Card style={{ height: "100%"}}>
                <Card.Img src={item.image.url}/>
                  
                <Card.Title>
                    {item.name }
                </Card.Title>
            </Card>
        </div>);
}


function SiteItems({ site, setItemId}) {
    const items = site.items.map(entry =>
        <Col key={entry.id} md={2}>
            <ItemCard key={entry.id}
                      item={entry}
                      onClick={setItemId}/>
        </Col>
    );
    
    return ( <Container className="mt-2">
                 <Row>       
                     { items }
                 </Row>
             </Container>
           );
}


function SiteImages({ site }) {
    const items = site.images.map(entry =>
        <Carousel.Item key={entry.url}>
            <Image src={entry.url}
                   style={{ maxWidth: "50vmin", maxHeight: "50vmin",
                            minHeight: "30vmin"}}/>
        </Carousel.Item>);

    return (
        <Carousel interval={null}>
            { items }
        </Carousel>            
    );
}


function Site({ world, siteId, onClose }) {
    const [site, setSite] = useState(null);
    const [view, setView] = useState(null);
    const [characterId, setCharacterId] = useState(null);
    const [itemId, setItemId] = useState(null);    
    
    useEffect(() => {
        let ignore = false;

        async function getData() {
            // Load the site
            const url = URL + "/worlds/" + world.id +
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
    }, [world, siteId, itemId]);

    async function takeItem(item_id) {
        // Set player location
        const url = URL + "/worlds/" + world.id + "/command";
        const data = { "name": "take",
                       "item": item_id }
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: JSON.stringify(data),
                headers: {
                    'Content-Type': 'application/json',
                    "Authorization": "Bearer " + AUTH_KEY
                }
            });
            await response.json();
            setItemId(item_id);
        } catch {
            console.log("ERROR");
        }
    }
    

    function clearView() {
        setView(null)
    }

    function clearCharacterId() {
        setCharacterId(null)
    }

    function clickClose() {
        onClose()
    }

    if (!site) {
        return <div/>        
    }

    if (view) {
        return (<DetailsView view={view} world={ world }
                             onClose={clearView}/>);
    }

    if (characterId) {
        return (
            <ChatCharacter worldId={world.id}
                           characterId={characterId}
                           onClose={clearCharacterId}/>
        );
    }
    
    return (
        <Container>
            <Row>
                <Navigation onClose={clickClose} setView={ setView }/>
            </Row>
            <Row>
                <Col xs={6}>
                    <Stack>
                        <SiteImages site={site}/>
                    </Stack>
                </Col>
                <Col xs={6} style={{ textAlign: "left" }}>
                    <h2>{site.name}</h2>
                    <h5>{site.description}</h5>
                </Col>                        
            </Row>
            <Row className="mb-2">
                <SitePeople site={site}
                            setCharacterId={setCharacterId}/>
            </Row>
            <Row>
                <SiteItems site={site}
                           setItemId={takeItem}/>
            </Row>
        </Container>            
    );
}
    

function CloseBar({ onClose }) {
    return (
        <Navbar expand="lg" className="bg-body-tertiary">
            <Container>
                <CloseButton onClick={onClose}/>
            </Container>
        </Navbar>);
}

function Navigation({ onClose, setView}) {

    function setCharactersView() {
        setView("characters");        
    }
    
    function setItemsView() {
        setView("items");        
    }

    
    return (
        <Navbar expand="lg" className="bg-body-tertiary">
            <Container>
                <CloseButton onClick={onClose}/>
                <Nav>
                    <Nav.Link onClick={setCharactersView}>
                        Characters
                    </Nav.Link>
                    <Nav.Link onClick={setItemsView}>
                        Items
                    </Nav.Link>                        
                </Nav>
            </Container>
        </Navbar>);
}


function CharacterListEntry({ character }) {

    let has_support = "";
    if (character.givenSupport) {
        has_support = <i className="bi-heart" style={{ fontSize: "4rem"}}/>
    }

    return (
        <div className="card mb-3 container">
            <div className="row">
                <div className="col-2">
                    <img src={character.image.url} className="card-img"
                         alt="character"/>
                </div>
                <div className="col-8">
                    <div className="card-body">
                        <h5 className="card-title">
                            { character.name }
                        </h5>
                        <p className="card-text" style={{ textAlign: "left" }}>
                            { character.description }
                        </p>
                    </div>
                </div>
                <div className="col-2">
                    { has_support }
                </div>
            </div>
        </div>
    );
}

function CharacterList({ worldId }) {

    const [characterList, setCharacterList] = useState([]);

    useEffect(() => {
        let ignore = false;

        async function getCharacterData() {
            // Get the status of progress in the world
            const url = URL + "/worlds/" + worldId + "/characters";
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

    
    const entries = characterList.map(entry =>
        <CharacterListEntry key={entry.id}
                            character={entry}/>
    );

    return (
        <Stack className="mt-3">
            { entries }
        </Stack>
    );
}

function ItemListEntry({ item }) {

    let in_inventory = "";
    if (item.have_item) {
        in_inventory = <i className="bi-check" style={{ fontSize: "4rem"}}/>
    }
    
    return (
        <div className="card mb-3 container">            
            <div className="row">
                <div className="col-2">
                    <img src={item.image.url} className="card-img"
                         alt="item"/>
                </div>
                <div className="col-8">
                    <div className="card-body">
                        <h5 className="card-title">
                            { item.name }
                        </h5>
                        <p className="card-text" style={{ textAlign: "left" }}>
                            { item.description }
                        </p>
                    </div>
                </div>
                <div className="col-2">
                    { in_inventory }
                </div>
            </div>
        </div>
    );
}

function ItemList({ worldId }) {

    const [itemList, setItemList] = useState([]);

    useEffect(() => {
        let ignore = false;

        async function getItemData() {
            // Get the status of progress in the world
            const url = URL + "/worlds/" + worldId + "/items";
            try {
                const response =
                      await fetch(url, {
                          headers: {
                              "Authorization": "Bearer " + AUTH_KEY
                          }
                      });
                const values = await response.json();
                if (!ignore) {
                    setItemList(values);
                }
            } catch {
            }
        }
        
        getItemData();
        return () => {
            ignore = true;
        }
    }, [worldId]);

    
    const entries = itemList.map(entry =>
        <ItemListEntry key={entry.id}
                       item={entry}/>
    );

    return (
        <Stack className="mt-3">
            { entries }
        </Stack>
    );
}

function DetailsView({view, world, onClose}) {

    if (view === "characters") {
        return (
            <div>
                <h2>
                    {world.name} Characters
                </h2>
                <CloseBar onClose={onClose}/>
                <CharacterList worldId={world.id}/>
            </div>
        );        
    } else {
        return (
            <div>
                <h2>
                    {world.name} Items
                </h2>
                <CloseBar onClose={onClose}/>
                <ItemList worldId={world.id}/>                
            </div>
        );        
    }
}




function SiteItem({ site, onClick }) {
    function handleClick() {
        onClick(site.id);
    }
    return (
        <div onClick={handleClick}  className="mt-2" style={{ height: "100%"}}>
            <Card style={{ height: "100%"}}>
                <Card.Img src={site.image.url}/>
                <Card.Title>
                    { site.name }
                </Card.Title>
            </Card>
        </div>);
}



function WorldSites({ siteList, onClick }) {

    const sites = siteList.map(entry =>
        <Col key={entry.id} md={2}>
            <SiteItem key={entry.id}
                           site={entry}
                           onClick={onClick}/>
        </Col>
    );
    
    return ( <Container className="mt-2">
                 <Row>                 
                     { sites }
                 </Row>
             </Container>
           );
}

function WorldImages({world}) {
    const items = world.images.map(entry =>
        <Carousel.Item key={entry.url}>
            <Image src={entry.url}
                   style={{ maxWidth: "50vmin", maxHeight: "50vmin",
                            minHeight: "30vmin"}}/>
        </Carousel.Item>);
            
    return (
        <Carousel interval={null}>
            { items }
        </Carousel>            
    );
}




function World({ worldId, setWorldId }) {
    const [world, setWorld] = useState(null);            
    const [siteList, setSiteList] = useState([]);
    const [siteId, setSiteId] = useState(null);
    const [view, setView] = useState(null);

    
    useEffect(() => {
        let ignore = false;

        async function getSiteData() {
            // Get the status of progress in the world
            const url = URL + "/worlds/" + worldId + "/sites";
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
                    values.forEach(item => {
                        if (item.present) {
                            setSiteId(item.id);
                        }});
                }
            } catch {
            }
        }

        async function getWorldData() {
            // Get the details of the world
            const url = URL + "/worlds/" + worldId;
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

    function clearView() {
        setView("");
    }

    function clearSite() {
        goToSite(""); 
        setSiteId(null);
    }

    function selectSite(site_id) {
        goToSite(site_id);
        setSiteId(site_id);
    }

    async function goToSite(site_id) {
        // Set player location
        const url = URL + "/worlds/" + worldId + "/command";
        const data = { "name": "go",
                       "to": site_id }
        try {
            await fetch(url, {
                method: 'POST',
                body: JSON.stringify(data),
                headers: {
                    'Content-Type': 'application/json',
                    "Authorization": "Bearer " + AUTH_KEY
                }
            });
        } catch {
            console.log("ERROR");
        }
    }


    // Wait until data loads
    if (world === null || siteList === null) {
        return (<div></div>);
    }

    if (view) {
        return (<DetailsView view={view} world={ world } onClose={clearView}/>);
    }

    // Show a specific site
    if (siteId) {
        return (<Site world={world}
                      siteId={siteId}
                      onClose={clearSite}/>);
    }

    // Show world view
    // Show sites
    return (
        <Container>
            <Row>
                <Navigation onClose={clickClose} setView={ setView }/>
            </Row>
            <Row >
                <Col xs={6}>
                    <WorldImages world={world}/>
                </Col>
                <Col xs={6} style={{ textAlign: "left" }}>
                    <h2>{world.name}</h2>
                    <h5>{world.description}</h5>
                </Col>                        
            </Row>
            <Row>
                <WorldSites siteList={siteList} onClick={selectSite}/>
            </Row>
        </Container>            
    );
}


function WorldItem({ world, onClick }) {

    function handleClick() {
        onClick(world.id);
    }
    
    return (
        <div className="card mb-3 container" onClick={handleClick} >
            <div className="row">
                <div className="col-2">
                    <img src={world.image.url} className="card-img" alt="world"/>
                </div>
                <div className="col-8">
                    <div className="card-body">
                        <h5 className="card-title">
                            { world.name }
                        </h5>
                        <p className="card-text" style={{ textAlign: "left" }}>
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
            const url = URL + "/worlds";
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
        <Stack className="mt-3">
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
            const url = URL + "/initdata";
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

export default App;
