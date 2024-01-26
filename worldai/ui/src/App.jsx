import { get_url, headers_get, headers_post } from './util.js';
import { ElementImages, WorldItem, CloseBar } from './common.jsx';
import { getWorldList, getWorld, getPlayerData } from './api.js';
import { getSiteList, getItemList, getCharacterList } from './api.js';
import { getSite, getItem, getCharacter } from './api.js';

import ChatScreen from './ChatScreen.jsx';

import { useState } from 'react'
import { useEffect } from 'react';

import './App.css'

import Alert from 'react-bootstrap/Alert';
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



function CharacterScreen({ character }) {
  return (
    <Stack style={{ textAlign: "left" }}>
      <h3>{character.name}</h3>
      <ElementImages element={character}/>
      <h5>Notes:</h5>
      {character.description}
      <p>
        Have support: { character.givenSupport ? "Yes" : "No" }
      </p>
    </Stack>
  );
}

async function getCharacterChats(context) {
  const worldId = context.worldId
  const characterId = context.characterId  
  const url = `/threads/worlds/${worldId}/characters/${characterId}`;
  const response =
        await fetch(get_url(url),
                    { headers: headers_get() });
  const values = await response.json();

  if (values["messages"].length === 0) {
    const response = await postCharacterChat(context, "");
    values["messages"] = [response]
  }
  
  return values;
}

async function postCharacterChat(context, user_msg) {
  const worldId = context.worldId
  const characterId = context.characterId  
  const data = { "user": user_msg }
  const url = `/threads/worlds/${worldId}/characters/${characterId}`;
  // Post the user request
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()
  });
  const values = await response.json();
  return values;
}

function ChatCharacter({ world, characterId,
                         playerData,
                         setPlayerData,
                         setView,
                         statusMessage, selectedItem,
                         useItem,
                         onClose, onChange}) {
  const [character, setCharacter] = useState(null);
  const [context, setContext ] = useState(
    {
      "worldId": world.id,
      "characterId": characterId
    });  
  useEffect(() => {
    let ignore = false;
    async function getData() {
      // Load the character
      try {
        const value = await getCharacter(world.id, characterId);
        if (!ignore) {
          setCharacter(value);
        }
      } catch (e) {
        console.log(e);        
      }
    }
    getData();
    return () => {
      ignore = true;
    }
  }, [world, characterId]);

  async function handleChatChange() {
    // Chat signaled state change on server side
    // Reload player and character
    console.log("handle chat change");
    try {
      let calls = Promise.all([ getCharacter(world.id, characterId),
                                getPlayerData(world.id)]);
      let [character, player] = await calls;
      console.log("set character");
      console.log("set player data");
      setCharacter(character);
      setPlayerData(playerData);
    } catch (e) {
      console.log(e);
    }
    // Let parent component know
    onChange();
  }

  function clearView() {
    setView(null)
  }

  if (!character) {
    return <div/>
  }

  let item_card = "";
  if (selectedItem !== null) {
    item_card = (<ItemCard item={selectedItem}
                           no_title={ true }
                           action={ "Use" }
                           onClick={ useItem }/>);
  }

  return (
    <Container>
      <Row>
        <Navigation onClose={onClose} setView={ setView }/>
      </Row>
      <Row>
        <Col xs={6}>
          <Stack>
            <CharacterScreen character={character}/>
            <Container>
              <Row>
                <Col xs={8}>
                  <Alert className="mt-3">              
                    { statusMessage }
                  </Alert>

                </Col>
                <Col xs={4}>
                  { item_card }
                </Col>
              </Row>
            </Container>
          </Stack>
        </Col>
        <Col xs={6}>
            <ChatScreen name={character.name}
                        context={context}
                        getChats={getCharacterChats}
                        postChat={postCharacterChat}
                        onChange={handleChatChange}/>
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
    <div className="mt-2">
      <Card style={{ maxWidth:"15vmin",  padding: "1em" }}>      
        <Card.Img src={character.image.url}/>
        <Card.Title>
          {character.name }
        </Card.Title>
        <Button onClick={handleClick} className="mt-auto">Chat</Button>
      </Card>
    </div>);
}

function getSitePeople(site, setCharacterId) {

    return site.characters.map(entry =>
    <Col key={entry.id} md={2}>
      <CharacterItem key={entry.id}
                     character={entry}
                     onClick={setCharacterId}/>
    </Col>
  );
}

function ItemCard({ item, no_title, action, onClick }) {
  function handleClick() {
    if (onClick) {
      onClick(item.id);
    }
  }
  return (
    <div className="mt-2">
      <Card style={{ maxWidth:"15vmin",  padding: "1em" }}>
        <Card.Img src={item.image.url}/>
        
        <Card.Title>
          { no_title ? "" : item.name }
        </Card.Title>
        <Button onClick={handleClick} className="mt-auto">
          { action }
        </Button>        
      </Card>
    </div>);
}


function getSiteItems(site, useItemId, takeItemId) {
  return site.items.map(entry =>
    <Col key={entry.id} md={2}>
      <ItemCard key={entry.id}
                item={entry}
                action={ entry.mobile ? "Take" : "Use" }
                onClick={ entry.mobile ? takeItemId : useItemId }/>
    </Col>
  );
}


async function postTakeItem(worldId, itemId) {
  const url = `/worlds/${worldId}/command`;
  const data = { "name": "take",
                 "item": itemId }
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()    
  });
  return response.json();
}


async function postSelectItem(worldId, itemId) {
  const url = `/worlds/${worldId}/command`;
  const data = { "name": "select",
                 "item": itemId }
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()    
  });
  return response.json();
}


async function postUseItem(worldId, itemId) {
  const url = `/worlds/${worldId}/command`;
  const data = { "name": "use",
                 "item": itemId }
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()    
  });
  return response.json();
}

function Site({ world, siteId,
                playerData, setPlayerData,
                selectedItem, selectItem,
                statusMessage, setStatusMessage,
                onClose }) {
  const [site, setSite] = useState(null);
  const [view, setView] = useState(null);
  const [characterId, setCharacterId] = useState(null);
  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      // Load the site
      try {
        const value = await getSite(world.id, siteId)
        if (!ignore) {
          setSite(value);
          setCharacterId(value.chatting);
        }
      } catch (e) {
        console.log(e);        
      }
    }
    getData();
    return () => {
      ignore = true;
    }
  }, [world, siteId]);

  async function reloadState() {
    try {
      let calls = Promise.all([ getSite(world.id, siteId),
                                getPlayerData(world.id)]);
      let [site, player] = await calls;
      console.log("set site");
      console.log("set player data");
      setSite(site);
      setPlayerData(playerData);
    } catch (e) {
      console.log(e);
    } 
  }

  async function takeItem(item_id) {
    try {
      let response = await postTakeItem(world.id, item_id);
      setStatusMessage(response.message)
      if (response.changed) {
        reloadState()
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  async function useItem(item_id) {
    try {
      // TODO: display some type of result here
      let response = await postUseItem(world.id, item_id);
      setStatusMessage(response.message)
      if (response.changed) {
        reloadState()
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  async function useSelectedItem() {
    if (selectedItem !== null) {
      useItem(selectedItem.id);
    }
  }

  function handleChanges() {
    console.log("site handle changes - reload state");
    reloadState();
  }
  
  function clearView() {
    setView(null)
  }

  function clickClose() {
    onClose()
  }

  if (!site) {
    return <div/>        
  }

  async function engageCharacter(char_id) {
    try {    
      const response = await postEngage(world.id, char_id);
      setCharacterId(char_id);
      setStatusMessage(response.message);      
    } catch (e) {
      console.log(e);
    }
  }

  async function disengageCharacter() {
    try {    
      await postEngage(world.id, null);
      setCharacterId(null);
      setStatusMessage("");      
    } catch (e) {
      console.log(e);
    }
  }
  

  if (view) {
    return (<DetailsView view={view}
                         world={ world }
                         selectItem={selectItem}
                         onClose={clearView}/>);
  }

  if (characterId) {
    return (
      <ChatCharacter world={world}
                     characterId={characterId}
                     playerData={playerData}
                     setPlayerData={setPlayerData}
                     setView={setView}
                     statusMessage={statusMessage}
                     selectedItem={selectedItem}
                     useItem={useSelectedItem}
                     onClose={disengageCharacter}
                     onChange={handleChanges}/>
    );
  }

  let item_card = "";
  if (selectedItem !== null) {
    item_card = (<ItemCard item={selectedItem}
                           action={ "Use" }
                           onClick={useSelectedItem}/>);
  }
  
  return (
    <Container>
      <Row>
        <Navigation onClose={clickClose} setView={ setView }/>
      </Row>
      <Row>
        <Col xs={6}>
          <Stack>
            <ElementImages element={site}/>
            <Alert className="m-3">
              { statusMessage }
            </Alert>
          </Stack>
        </Col>
        <Col xs={6} style={{ textAlign: "left" }}>
          <Stack>
            <h2>{site.name}</h2>
            <h5>{site.description}</h5>
            { item_card }
          </Stack>
        </Col>
      </Row>
      <Row className="mb-2">
        <Stack direction="horizontal">
          { getSitePeople(site, engageCharacter) }
          { getSiteItems(site, useItem, takeItem) }
        </Stack>
      </Row>
    </Container>            
  );
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
            Inventory
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
      try {
        const values = await getCharacterList(worldId);
        if (!ignore) {
          setCharacterList(values);
        }
      } catch (e) {
        console.log(e);      
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

function ItemListEntry({ item, selectItem}) {

  let in_inventory = "";
  if (item.have_item) {
    in_inventory = <i className="bi-check" style={{ fontSize: "4rem"}}/>
  }

  function handleClick() {
    if (selectItem) {
      selectItem(item.id);
    }
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
          <Button onClick={handleClick}
                  disabled={selectItem === null}                  
                  className="mt-auto">
            Select
          </Button>        
        </div>
      </div>
    </div>
  );
}


function Inventory({ worldId, selectItem }) {

  const [itemList, setItemList] = useState([]);

  useEffect(() => {
    let ignore = false;

    async function getItemData() {
      try {
        const values = await getItemList(worldId);
        if (!ignore) {
          setItemList(values);
        }
      } catch (e) {
        console.log(e);
      }
    }
    
    getItemData();
    return () => {
      ignore = true;
    }
  }, [worldId]);

  const entries = itemList.filter(
    entry => entry.have_item).map(
      entry => <ItemListEntry key={entry.id}
                              item={entry}
                              selectItem={selectItem}/>);
  
  return (
    <Stack className="mt-3">
      { entries }
    </Stack>
  );
}

function DetailsView({view, world, selectItem, onClose}) {

  function onSelect(item_id) {
    if (typeof selectItem !== 'undefined') {    
      selectItem(item_id)
      onClose()
    }
  }
  
  if (view === "characters") {
    return (
      <div>
        <CloseBar onClose={onClose}/>
        <h5>
          {world.name} Characters
        </h5>
        <CharacterList worldId={world.id}/>
      </div>
    );        
  } else {
    return (
      <div>
        <CloseBar onClose={onClose}/>
        <h5>
          Inventory
        </h5>
        <Inventory worldId={world.id}
                   selectItem={ typeof selectItem !== 'undefined' ? onSelect : null}/>
      </div>
    );        
  }
}




function SiteItem({ site, onClick }) {
  function handleClick() {
    onClick(site.id);
  }

  return (
    <div className="mt-2" style={{ height: "100%"}}>
      <Card style={{ height: "100%", padding: "1em" }}>
        <Card.Img src={site.image.url}/>
        <Card.Title>
          { site.name }
        </Card.Title>
        <Button onClick={handleClick} className="mt-auto">Go</Button>        
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



async function postGoTo(worldId, siteId) {
  const url = `/worlds/${worldId}/command`;
  const data = { "name": "go",
                 "to": siteId }
  let result = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()        
  });
  return result.json();
}

async function postEngage(worldId, charId) {
  const url = `/worlds/${worldId}/command`;
  let data = null
  if (charId !== null) {
    data =  { "name": "engage",
              "character": charId }
  } else {
    data =  { "name": "disengage" }
  }
  
  let result = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()        
  });
  return result.json();
}

function World({ worldId, setWorldId }) {
  const [world, setWorld] = useState(null);            
  const [siteList, setSiteList] = useState([]);
  const [siteId, setSiteId] = useState(null);
  const [view, setView] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);  
  const [statusMessage, setStatusMessage] = useState("");
  const [playerData, setPlayerData] = useState(null);
  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        // Get the details of the world  and a list of sites.

        let calls = Promise.all([ getSiteList(worldId),
                                  getWorld(worldId),
                                  getPlayerData(worldId)]);
        let [sites, world, player] = await calls;

        if (!ignore) {
          setWorld(world);
          setSiteList(sites);
          setPlayerData(player);
          // Set the site id if we are present at a site
          for (let i = 0; i < sites.length; i++) {
            if (sites[i].present) {
              setSiteId(sites[i].id);
              break;
            }
          }
        }
      } 
      catch (e) {
        console.log(e);
      }
    }

    getData();
    return () => {
      ignore = true;
    }
  }, [worldId]);

  useEffect(() => {
    // Player Data has changed.
    // Update related state
    let ignore = false;
    console.log("player data changed");
    async function loadSelectedItem(item_id) {
      try {
        const item = await getItem(world.id, item_id);
        if (!ignore) {
          console.log("set selected item");
          setSelectedItem(item);
        }
      } 
      catch (e) {
        console.log(e);
      }
    }

    if (playerData !== null) {
      if (playerData.selected_item === null) {
        console.log("clear selected item");
        setSelectedItem(null);
      } else if (selectedItem === null) {
        console.log("load new selected item: '" + playerData.selected_item + "'");
        loadSelectedItem(playerData.selected_item);
      } else if (playerData.selected_item !== selectedItem.id) {
        console.log("change selected item");
        loadSelectedItem(playerData.selected_item);      
      } else {
        console.log("no change selected item");
      }
    }

    return () => {
      ignore = true;
    }
  }, [playerData]);

  function clickClose() {
    setWorldId("");
  }

  function clearView() {
    setView("");
  }

  function clearSite() {
    goToSite("");
    setStatusMessage("");
    setSiteId(null);
  }

  function selectSite(site_id) {
    goToSite(site_id);
    setStatusMessage("");    
    setSiteId(site_id);
  }

  async function reloadPlayerData() {
    try {
      console.log("reload player data");
      const playerData = await getPlayerData(world.id);
      setPlayerData(playerData);
    } catch (e) {
      console.log(e);
    } 
  }
  
  async function selectItem(item_id) {
    try {
      let response = await postSelectItem(world.id, item_id);
      setStatusMessage(response.message)
      if (response.changed) {
        reloadPlayerData();
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }
  
  async function goToSite(site_id) {
    try {    
      await postGoTo(world.id, site_id);      
    } catch (e) {
      console.log(e);
    }
  }


  // Wait until data loads
  if (world === null || siteList === null) {
    return (<div></div>);
  }

  if (view) {
    return (<DetailsView view={view}
                         world={ world }
                         selectItem={ selectItem }
                         onClose={clearView}/>);
  }

  // Show a specific site
  if (siteId) {
    return (<Site world={world}
                  siteId={siteId}
                  playerData={playerData}
                  setPlayerData={setPlayerData}
                  selectedItem={selectedItem}
                  selectItem={selectItem}
                  statusMessage={statusMessage}
                  setStatusMessage={setStatusMessage}
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
          <ElementImages element={world}/>
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


function SelectWorld({setWorldId}) {
  const [worldList, setWorldList] = useState([]);
  useEffect(() => {
    let ignore = false;

    async function getData() {
      // Get the list of worlds
      try {
        const values = await getWorldList();
        if (!ignore) {
          setWorldList(values);
        }
      } catch (e) {
        console.log(e);
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

async function getInitData() {
  const response =
        await fetch(get_url("/initdata"),
                    { headers: headers_get() });
  const values = await response.json();
  return values; 
}

function PlayClient() {
  const [worldId, setWorldId] = useState(null);
  useEffect(() => {
    let ignore = false;

    async function getData() {
      // Get initial load data
      try {
        const values = await getInitData();
          if (!ignore) {
            setWorldId(values['world_id']);
          }
      } catch (e) {
        console.log(e);
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


export { PlayClient };
export default PlayClient;

