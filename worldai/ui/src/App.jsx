import { get_url, headers_get, headers_post } from './util.js';
import { ElementImages, WorldItem, CloseBar } from './common.jsx';
import { getWorldList, getWorld, getWorldStatus, resetWorldState, getSiteList } from './api.js';
import { getSiteInstancesList, getItemInstancesList, getCharacterInstancesList } from './api.js';
import { getSiteInstance, getItemInstance, getCharacter, getCharacterData } from './api.js';

import ChatScreen from './ChatScreen.jsx';

import { useState } from 'react'
import { useEffect } from 'react';
import { useRef } from 'react';

import './App.css'

import Alert from 'react-bootstrap/Alert';
import Button from 'react-bootstrap/Button';
import CloseButton from 'react-bootstrap/CloseButton';
import Card from 'react-bootstrap/Card';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Table from 'react-bootstrap/Table';
import Image from 'react-bootstrap/Image';
import Stack from 'react-bootstrap/Stack';

import Modal from 'react-bootstrap/Modal';

import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import NavDropdown from 'react-bootstrap/NavDropdown';
import ModalHeader from 'react-bootstrap/esm/ModalHeader.js';

function getFriendship(level) {
  let friend_icon = "bi bi-emoji-neutral";
  if (level > 0) {
    friend_icon = "bi bi-emoji-smile";
  }
  if (level > 5) {
    friend_icon = "bi bi-emoji-grin";
  }
  if (level < 0) {
    friend_icon = "bi bi-emoji-frown";
  }
  if (level < -5) {
    friend_icon = "bi bi-emoji-angry";
  }
  return friend_icon;
}

function getCharStates(charStats) {
  let state = [];
  if (charStats.health < 1) {
    state.push(<i key="dead" className="bi bi-person-x" title="Dead"/>);    
  }
  if (charStats.health < 100) {  
    state.push(<i key="health" className="bi bi-bandaid" title="Injured"/>);
  }
  if (charStats.invisible) {
    state.push(<i key="invisible" className="bi bi-eye-slash" title="Invisible"/>);
  }
  if (charStats.poisoned) {
    state.push(<i key="poisoned" className="bi bi-exclamation-circle" title="Poisoned"/>);
  } 
  if (charStats.sleeping) {
    state.push(<i key="sleeping" className="bi bi-lightbulb-off" title="Sleeping"/>);
  }
  if (charStats.paralized) {
    state.push(<i key="paralized" className="bi bi-emoji-dizzy" title="Paralized"/>);
  }
  if (charStats.brainwashed) {
    state.push(<i key="brainwashed" className="bi bi-emoji-sunglasses" title="Brainwashed"/>);
  }
  return state;
}

function CharacterStats({ charStats }) {
  let friend_icon = getFriendship(charStats.friendship);
  let health = [];
  for (let i = 0; i < 10; i++) {
    if (i < charStats.health / 10) {
      health.push(<i key={i} className="bi bi-heart-fill"/>);
    } else {
      health.push(<i key={i} className="bi bi-heart"/>);
    }
  }
  
  let state = getCharStates(charStats);
  return (
    <Table striped bordered hover>
      <thead>
        <tr>
          <th>{ charStats.name } Health</th>
          <th>State</th>          
          <th>Feel</th>
        </tr>
      </thead>
      <tbody>      
        <tr>
          <td>
            <Stack direction="horizontal">
              {health}
            </Stack>
          </td>            
          <td>
            <Stack direction="horizontal">
              {state}
            </Stack>
          </td>            
          <td><i className={friend_icon}/></td>
        </tr>
      </tbody>
    </Table>
  );
}

function PlayerStats({ charStats }) {
  let state = getCharStates(charStats);  
  let health = [];
  for (let i = 0; i < 10; i++) {
    if (i < charStats.health / 10) {
      health.push(<i key={i} className="bi bi-heart-fill"/>);
    } else {
      health.push(<i key={i} className="bi bi-heart"/>);
    }
  }
  return (
    <Table striped bordered hover>
      <thead>
        <tr>
          <th>Player Health</th>
          <th>State</th>          
        </tr>
      </thead>
      <tbody>      
        <tr>
          <td>{ health }</td>
          <td>
            <Stack direction="horizontal">
              { state }
            </Stack>
          </td>
        </tr>
      </tbody>
    </Table>
  );
}

function CharacterScreen({ character }) {
  return (
    <Stack style={{ textAlign: "left" }}>
      <h3>{character.name}</h3>
      <ElementImages element={character}/>
      <h5>Notes:</h5>
      {character.description}
    </Stack>
  );
}

async function getCharacterChats(context) {
  const worldId = context.worldId
  const characterId = context.characterId  
  const url = `/worlds/${worldId}/characters/${characterId}/thread`;
  const response =
        await fetch(get_url(url),
                    { headers: headers_get() });
  const values = await response.json();
  return values.history_response;
}

async function postChatStart(context, user_msg) {
  const worldId = context.worldId
  const characterId = context.characterId  
  const data = { "command": "start",
                 "user": user_msg }
  const url = `/worlds/${worldId}/characters/${characterId}/thread`;
  // Post the user request
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()
  });
  const values = await response.json();
  return values;
}

async function postChatContinue(context, msg_id) {
  const worldId = context.worldId
  const characterId = context.characterId  
  const data = { "command": "continue",
                 "msg_id": msg_id }
  const url = `/worlds/${worldId}/characters/${characterId}/thread`;
  // Post the user request
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()
  });
  const values = await response.json();
  return values;
}

async function postActionStart(context, args) {
  const worldId = context.worldId
  const characterId = context.characterId
  const data = { "command": "start",
                 "action": args.action,
                 "item": args.itemId }
  const url = `/worlds/${worldId}/characters/${characterId}/action`;
  // Post action
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()
  });
  const values = await response.json();
  return values;
}

async function postActionContinue(context, args) {
  const worldId = context.worldId
  const characterId = context.characterId
  const data = { "command": "continue",
                 "action": args.action, 
                 "item": args.itemId }
  const url = `/worlds/${worldId}/characters/${characterId}/action`;
  // Post next step in action
  const response = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()
  });
  const values = await response.json();
  return values;
}

function ChatCharacter({ world, setWorldId, setSiteId, characterId,
                         playerData,
                         setView,
                         statusMessage, setStatusMessage,
                         selectedItem,
                         currentTime,  setCurrentTime,
                         onClose, onChange}) {
  const [character, setCharacter] = useState(null);
  const [characterData, setCharacterData] = useState(null);
  const [chatEnabled, setChatEnabled] = useState(true);
  const [context, setContext ] = useState(
    {
      "worldId": world.id,
      "characterId": characterId
    });
  // Hook to a function defined in the ChatScreen to run an action
  const submitActionRef = useRef(null);
  
  useEffect(() => {
    let ignore = false;
    async function getData() {
      // Load the character
      try {
        let calls = Promise.all([ getCharacter(world.id, characterId),
                                  getCharacterData(world.id, characterId)]);
        const [character, characterData] = await calls;
                                  
        if (!ignore) {
          setCharacter(character);
          setCharacterData(characterData);
          setChatEnabled(characterData.can_chat);
          console.log("current time: " + characterData.current_time)
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

  useEffect(() => {
    setContext({
      "worldId": world.id,
      "characterId": characterId
    });
  }, [ selectedItem ]);

  
  async function reloadState() {
    // Chat signaled state change on server side
    // Reload player and character
    try {
      let calls = Promise.all([ getCharacter(world.id, characterId),
                                getCharacterData(world.id, characterId)]);
      const [character, characterData] = await calls;
      
      setCharacter(character);
      setCharacterData(characterData);
      setChatEnabled(characterData.can_chat);
      
    } catch (e) {
      console.log(e);
    }
    // Let parent component know
    onChange();
  }

  if (!character) {
    return <div/>
  }

  async function useSelectedItem() {
    if (selectedItem !== null && submitActionRef.current !== null) {
      const args = {
        "action": "use",
        "itemId": selectedItem.id
      }
      submitActionRef.current.submitAction(args);
    }
  }

  async function runChatStart(context, user_msg) {
    let values = await postChatStart(context, user_msg);
    setStatusMessage(values.world_status.response_message)
    if (values.world_status.changed) {
      reloadState();
    }
    setCurrentTime(values.world_status.current_time)
    return values.chat_response
  }

   async function runChatContinue(context, msg_id) {
    let values = await postChatContinue(context, msg_id);
    setStatusMessage(values.world_status.response_message)
    setCurrentTime(values.world_status.current_time)
    if (values.world_status.changed) {
      reloadState();
    }
    return values.chat_response
  }
 
  async function startCharacterAction(context, args) {
    let values = await postActionStart(context, args);
    setStatusMessage(values.world_status.response_message)
    setCurrentTime(values.world_status.current_time)
    if (values.world_status.changed) {
      reloadState();
    }
    return values.chat_response
  }
  
  async function continueCharacterAction(context, msg_id) {
    let values = await postActionContinue(context, msg_id);
    if (values.world_status.response_message.length > 0) {
      setStatusMessage(values.world_status.response_message)
    }
    setCurrentTime(values.world_status.current_time)
    if (values.world_status.changed) {
      reloadState();
    }
    return values.chat_response
  }
  
  let item_card = "";
  if (selectedItem !== null) {
    item_card = (<ItemCard item={selectedItem}
                           no_title={ true }
                           action={ "Use" }
                           onClick={ useSelectedItem }/>);
  }

  const calls = {
    context: context,
    getChats: getCharacterChats,
    postChat: runChatStart,
    continueChat: runChatContinue,
    clearChat: null,
    startChatAction: startCharacterAction,
    continueChatAction: continueCharacterAction
  };
  
  
  return (
    <Container>
      <Row>
        <Navigation time={currentTime}
                    onClose={onClose}
                    world={world}
                    setWorldId={setWorldId}
                    setSiteId={setSiteId}
                    setView={ setView }/>
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
                  <CharacterStats charStats={characterData}/>
                  <PlayerStats charStats={playerData.status}/>
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
                        calls={calls}
                        chatEnabled={chatEnabled}
                        ref={submitActionRef}/>
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
    <Col key={entry.id} xs={4} sm={3} lg={2}>
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

async function postDropItem(worldId, itemId, char_id) {
  const url = `/worlds/${worldId}/command`;
  const data = { "name": "drop",
                 "item": itemId }
  if (char_id != null) {
    data["character"] = char_id
  }

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

function Site({ world, setWorldId, siteId, setSiteId,
                playerData, setPlayerData,
                selectedItem, setSelectedItem,
                selectItem, 
                statusMessage, setStatusMessage,
                currentTime,  setCurrentTime,
                characterId, setCharacterId,
                onClose }) {
  const [site, setSite] = useState(null);
  const [view, setView] = useState(null);
  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      // Load the site
      try {
        const value = await getSiteInstance(world.id, siteId)
        if (!ignore) {
          setSite(value);
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

  async function reloadSiteState() {
    try {
      let calls = Promise.all([ getWorldStatus(world.id), getSiteInstance(world.id, siteId) ]);
      let [newWorldStatus, newSite] = await calls;
      setSite(newSite);
      setPlayerData(newWorldStatus.player);
      setCurrentTime(newWorldStatus.current_time);
      // Reset selected item if necessary
      if (newWorldStatus.player.selected_item === "") {
        setSelectedItem(null);
      }
    } catch (e) {
      console.log(e);
    } 
  }

  async function takeItem(item_id) {
    try {
      let response = await postTakeItem(world.id, item_id);
      setStatusMessage(response.world_status.response_message)
      setCurrentTime(response.world_status.current_time);
      if (response.world_status.changed) {
        reloadSiteState()
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  async function siteDropItem(item_id) {
    try {
      let response = await postDropItem(world.id, item_id, characterId);
      setStatusMessage(response.world_status.response_message);
      if (response.world_status.changed) {
        reloadSiteState()
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  async function useItem(item_id) {
    // Use item not in the presence of a character
    try {
      // TODO: display some type of result here
      let response = await postUseItem(world.id, item_id);
      setStatusMessage(response.world_status.response_message)
      setCurrentTime(response.world_status.current_time);
      if (response.world_status.changed) {
        reloadSiteState()
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
    reloadSiteState();
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
      setCharacterId(response.world_status.engaged_character_id);
      setStatusMessage(response.world_status.response_message);      
      setCurrentTime(response.world_status.current_time);
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
                         dropItem={siteDropItem}
                         onClose={clearView}/>);
  }

  if (characterId) {
    return (
      <ChatCharacter world={world}
                     setWorldId={setWorldId}
                     setSiteId={setSiteId}
                     characterId={characterId}
                     playerData={playerData}
                     setView={setView}
                     statusMessage={statusMessage}
                     setStatusMessage={setStatusMessage}                     
                     selectedItem={selectedItem}
                     currentTime={currentTime}
                     setCurrentTime={setCurrentTime}
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
        <Navigation time={currentTime}
                    world={world}
                    setWorldId={setWorldId}
                    setSiteId={setSiteId}
                    onClose={clickClose}
                    setView={ setView }/>
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
            <PlayerStats charStats={playerData.status}/>
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


function getTimeString(time) {
  // Convert time in minutes to days, hours, min
  let days = Math.floor(time / (60 * 24));
  time = time - (days * 60 * 24);
  let hours = Math.floor(time / 60);
  let minutes = time - (hours * 60 );
  return ("Day " + (days + 1) + " " +
          hours.toLocaleString('en-US',  {minimumIntegerDigits: 2,
                                          useGrouping:false}) +
          ":" + 
          minutes.toLocaleString('en-US',  {minimumIntegerDigits: 2,
                                            useGrouping:false}));
  
}


function Navigation({ time, world, setWorldId, setSiteId, onClose, setView}) {
  const [showDialog, setShowDialog] = useState(false);

  function setCharactersView() {
    setView("characters");        
  }

  function setSitesView() {
    setView("sites");        
  }
 
  function setInventoryView() {
    setView("inventory");        
  }
  
  function setItemsView() {
    setView("items");        
  }
  
  function closeGame() {
    setWorldId("");
  }

  function showResetGame() {
    setShowDialog(true);
  }

  function closeDialog() {
    setShowDialog(false);
  }

  function resetGame() {
    setSiteId("")
    resetWorldState(world.id)
    setShowDialog(false);
  }

  let close_button = "";
  if (typeof onClose != 'undefined') {
    close_button = (<CloseButton onClick={onClose}/>);
  }

  return (
    <Navbar expand="lg" className="bg-body-tertiary">
      <Container>
        <Nav>
          <NavDropdown id="games" title="Game">
            <NavDropdown.Item onClick={closeGame}>Close Game</NavDropdown.Item>
            <NavDropdown.Item onClick={showResetGame}>Reset Game</NavDropdown.Item>
          </NavDropdown>
          <NavDropdown id="world" title="World">
            <NavDropdown.Item onClick={setCharactersView}>Characters</NavDropdown.Item>
            <NavDropdown.Item onClick={setItemsView}>Items</NavDropdown.Item>
            <NavDropdown.Item onClick={setSitesView}>Sites</NavDropdown.Item>
          </NavDropdown>
          <Nav.Link onClick={setInventoryView}>
            Inventory
          </Nav.Link>                        
        </Nav>
        <Navbar.Brand>Story Quest: { world.name }</Navbar.Brand>
        <Navbar.Text>{getTimeString(time)}</Navbar.Text>
        { close_button }
        <Modal show={showDialog} onHide={closeDialog}>
          <Modal.Header closeButton>
            <Modal.Title>Reset Game?</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <p>Reset game and discard all progress?</p>
          </Modal.Body>
          <Modal.Footer>
            <Button variant='primary' onClick={closeDialog}>Close</Button>
            <Button variant="secondary" onClick={resetGame}>Reset</Button>
          </Modal.Footer>
        </Modal>
      </Container>
    </Navbar>);
}


function CharacterListEntry({ character }) {
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
        const values = await getCharacterInstancesList(worldId);
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

function InventoryListEntry({ item, selectItem, dropItem}) {

  function selectClick() {
    if (selectItem) {
      selectItem(item.id);
    }
  }
  
  function dropClick() {
    if (selectItem) {
      dropItem(item.id);
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
              <br/>
              Ability: { item.ability }
            </p>
          </div>
        </div>
        <div className="col-1">
          <Button onClick={selectClick}
                  disabled={selectItem === null}                  
                  className="mt-auto">
            Select
          </Button>
        </div>
        <div className="col-1">
          <Button onClick={dropClick}
                  disabled={dropItem === null}                  
                  className="mt-auto">
            Drop
          </Button>
        </div>
      </div>
    </div>
  );
}


function ItemListEntry({ item, selectItem, dropItem}) {

  let in_inventory = "";
  if (item.have_item) {
    in_inventory = <i className="bi bi-check" style={{ fontSize: "4rem"}}/>
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
              <br/>
              Ability: { item.ability }
            </p>
          </div>
        </div>
       </div>
    </div>
  );
}

function ItemsList({ worldId }) {

  const [itemList, setItemList] = useState([]);

  useEffect(() => {
    let ignore = false;

    async function getItemData() {
      try {
        const values = await getItemInstancesList(worldId);
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

  let entries = itemList.map(entry => <ItemListEntry 
	    		      key={entry.id}
                              item={entry}/>);
  
  return (
    <Stack className="mt-3">
      { entries }
    </Stack>
  );
}


function Inventory({ worldId, selectItem, dropItem }) {

  const [itemList, setItemList] = useState([]);

  useEffect(() => {
    let ignore = false;

    async function getItemData() {
      try {
        const values = await getItemInstancesList(worldId);
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

  let entries = itemList.filter(
    entry => entry.have_item).map(
      entry => <InventoryListEntry 
	    		      key={entry.id}
                              item={entry}
                              selectItem={selectItem}
                              dropItem={dropItem}/>);
  
  if (entries.length === 0) {
    entries = (<Alert className="m-3">
                Inventory is empty.
              </Alert>);
  }
  return (
    <Stack className="mt-3">
      { entries }
    </Stack>
  );
}

function SitesListEntry({ site }) {

  return (
    <div className="card mb-3 container">            
      <div className="row">
        <div className="col-2">
          <img src={site.image.url} className="card-img"
               alt="site"/>
        </div>
        <div className="col-8">
          <div className="card-body">
            <h5 className="card-title">
              { site.name }
            </h5>
            <p className="card-text" style={{ textAlign: "left" }}>
              { site.description }
            </p>
          </div>
        </div>
       </div>
    </div>
  );
}

function SitesList({ worldId }) {

  const [siteList, setSiteList] = useState([]);

  useEffect(() => {
    let ignore = false;

    async function getSiteData() {
      try {
        const values = await getSiteList(worldId);
        if (!ignore) {
          setSiteList(values);
        }
      } catch (e) {
        console.log(e);
      }
    }
    
    getSiteData();
    return () => {
      ignore = true;
    }
  }, [worldId]);

  let entries = siteList.map(entry => <SitesListEntry 
	    		      key={entry.id}
                              site={entry}/>);
  
  return (
    <Stack className="mt-3">
      { entries }
    </Stack>
  );
}


function DetailsView({view, world, selectItem, dropItem, onClose}) {

  function onSelect(item_id) {
    if (typeof selectItem !== 'undefined') {    
      selectItem(item_id)
      onClose()
    }
  }
  
  function onDrop(item_id) {
    if (typeof selectItem !== 'undefined') {    
      dropItem(item_id)
      onClose()
    }
  }
  
  if (view === "characters") {
    return (
      <div>
        <CloseBar title="Characters" onClose={onClose}/>
        <CharacterList worldId={world.id}/>
      </div>
    );        
  } else if (view === "items") {
    return (
      <div>
	    <CloseBar title="Items" onClose={onClose}/>
	    <ItemsList worldId={world.id}/>
      </div>
    );
  } else if (view === "sites") {
     return (
      <div>
	    <CloseBar title="Sites" onClose={onClose}/>
	    <SitesList worldId={world.id}/>
      </div>
    );
  } else {
    return (
      <div>
        <CloseBar title="Inventory" onClose={onClose}/>
        <Inventory worldId={world.id}
                   selectItem={ typeof selectItem !== 'undefined' ? onSelect : null}
                   dropItem={ typeof dropItem !== 'undefined' ? onDrop : null}
                   />
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
          { site.open ? "" : <i className="bi bi-lock-fill"/> }
        </Card.Title>
        <Button onClick={handleClick} className="mt-auto">Go</Button>        
      </Card>
    </div>);
}



function WorldSites({ siteList, onClick }) {

  const sites = siteList.map(entry =>
    <Col key={entry.id} xs={4} sm={3} lg={2}>
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
  const [currentTime, setCurrentTime] = useState(0);  
  const [characterId, setCharacterId] = useState(null);

  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        // Get the details of the world  and a list of sites.

        let calls = Promise.all([ getSiteInstancesList(worldId),
          getWorld(worldId),
          getWorldStatus(worldId)]);
        let [newSites, newWorld, newStatus] = await calls;

        if (!ignore) {
          setWorld(newWorld);
          setSiteList(newSites);
          setPlayerData(newStatus.player);
          setCurrentTime(newStatus.current_time);  // TODO - decide on this
          loadSelectedItem(newWorld, newStatus.player);
          setSiteId(newStatus.location_id);
          setCharacterId(newStatus.engaged_character_id);
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
  },  [worldId, siteId]);

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
  }

  async function loadSelectedItem(world, playerData) {
    try {    
      if (playerData.selected_item === "") {
        setSelectedItem(null);
      } else if (selectedItem === null) {
        // No currently selected item
        const newItem = await getItemInstance(world.id, playerData.selected_item);
        setSelectedItem(newItem);
      } else if (playerData.selected_item !== selectedItem.id) {
        const newItem = await getItemInstance(world.id, playerData.selected_item);        
        setSelectedItem(newItem);
      }
    } 
    catch (e) {
      console.log(e);
    }
  }
  
  async function updateWorldData() {
    // Reload player data and dependent information.
    try {
      let calls = Promise.all([ getSiteInstancesList(worldId),
        getWorldStatus(worldId)]);
      let [newSites, newWorldStatus] = await calls;

      setSiteList(newSites)
      setPlayerData(newWorldStatus.player);
      setSiteId(newWorldStatus.location_id);      
      loadSelectedItem(world, newWorldStatus.player);
    } catch (e) {
      console.log(e);
    }
      
  }
  
  async function selectItem(item_id) {
    try {
      let response = await postSelectItem(world.id, item_id);
      setStatusMessage(response.world_status.response_message)
      if (response.world_status.changed) {
        loadSelectedItem(world, response.world_status.player);
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }
  
    async function goToSite(site_id) {
      try {    
        let response = await postGoTo(world.id, site_id);
        console.log("post go to");
        setStatusMessage(response.world_status.response_message);    
        setCurrentTime(response.world_status.current_time);
        if (response.world_status.changed) {
          updateWorldData();
        }
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
                  setWorldId={setWorldId}
                  siteId={siteId}
                  setSiteId={setSiteId}
                  playerData={playerData}
                  setPlayerData={setPlayerData}
                  selectedItem={selectedItem}
                  setSelectedItem={setSelectedItem}
                  selectItem={selectItem}
                  statusMessage={statusMessage}
                  setStatusMessage={setStatusMessage}
                  currentTime={currentTime}
                  setCurrentTime={setCurrentTime}
                  characterId={characterId}
                  setCharacterId={setCharacterId}
                  onClose={clearSite}/>);
  }

  // Show world view
  // Show sites
  return (
    <Container>
      <Row>
        <Navigation time={currentTime}
                    world={world}
                    setWorldId={setWorldId}
                    setView={ setView }/>
      </Row>
      <Row >
        <Col xs={6}>
          <Stack>
            <ElementImages element={world}/>
            <Alert className="m-3">
              { statusMessage }
            </Alert>
          </Stack>
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

