//
// React Based Client App
//
//    Jim Wanderer
//    http://github.com/jmwanderer
//

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

function ChatCharacter({ worldData, worldStatus, setWorldStatus, clearDataCache,
                         statusMessage, setStatusMessage }) {
  const context =
    {
      "worldId": worldData.world.id,
      "characterId": worldData.character.id
    };
  // Hook to a function defined in the ChatScreen to run an action
  const submitActionRef = useRef(null);
  
  if (!worldData.character) {
    return <div/>
  }

  async function useSelectedItem() {
    if (worldData.selectedItem !== null && submitActionRef.current !== null) {
      const args = {
        "action": "use",
        "itemId": worldData.selectedItem.id
      }
      submitActionRef.current.submitAction(args);
    }
  }

  async function runChatStart(context, user_msg) {
    let values = await postChatStart(context, user_msg);
    setStatusMessage(values.world_status.response_message)
    setWorldStatus(values.world_status);
    if (values.world_status.changed) {
      clearDataCache();
    }
    return values.chat_response
  }

   async function runChatContinue(context, msg_id) {
    let values = await postChatContinue(context, msg_id);
    setStatusMessage(values.world_status.response_message)
    setWorldStatus(values.world_status);
    if (values.world_status.changed) {
      clearDataCache();
    }
    return values.chat_response
  }
 
  async function startCharacterAction(context, args) {
    let values = await postActionStart(context, args);
    setStatusMessage(values.world_status.response_message)
    setWorldStatus(values.world_status);
    if (values.world_status.changed) {
      clearDataCache();
    }
    return values.chat_response
  }
  
  async function continueCharacterAction(context, msg_id) {
    let values = await postActionContinue(context, msg_id);
    if (values.world_status.response_message.length > 0) {
      setStatusMessage(values.world_status.response_message)
    }
    setWorldStatus(values.world_status);
     if (values.world_status.changed) {
      clearDataCache();
    }
    return values.chat_response
  }
  
  let item_card = "";
  if (worldData.selectedItem !== null) {
    item_card = (<ItemCard item={worldData.selectedItem}
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
        <Col xs={6}>
          <Stack>
            <CharacterScreen character={worldData.character}/>
            <Container>
              <Row>
                <Col xs={8}>
                  <Alert className="mt-3">              
                    { statusMessage }
                  </Alert>
                  <CharacterStats charStats={worldData.characterData}/>
                  <PlayerStats charStats={worldStatus.player.status}/>
                </Col>
                <Col xs={4}>
                  { item_card }
                </Col>
              </Row>
            </Container>
          </Stack>
        </Col>
        <Col xs={6}>
            <ChatScreen name={worldData.character.name}
                        calls={calls}
                        chatEnabled={worldData.characterData.can_chat}
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

function getSiteCharacters(site, setCharacterId) {

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

function Site({ worldData, worldStatus, setWorldStatus, clearDataCache,
                statusMessage, setStatusMessage,
                onClose }) {
  
   async function engageCharacter(char_id) {
    try {    
      const response = await postEngage(worldData.world.id, char_id);
      setWorldStatus(response.world_status);
      setStatusMessage(response.world_status.response_message);      
    } catch (e) {
      console.log(e);
    }
  }

  async function takeItem(item_id) {
    try {
      let response = await postTakeItem(worldData.world.id, item_id);
      setWorldStatus(response.world_status);
      setStatusMessage(response.world_status.response_message)
      if (response.world_status.changed) {
        clearDataCache();
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
      let response = await postUseItem(worldData.world.id, item_id);
      setStatusMessage(response.world_status.response_message)
      setWorldStatus(response.world_status);
       if (response.world_status.changed) {
        clearDataCache();
      }
   } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  async function useSelectedItem() {
    if (worldData.selectedItem !== null) {
      useItem(worldData.selectedItem.id);
    }
  }
  let item_card = "";

  if (worldData.selectedItem !== null) {
    item_card = (<ItemCard item={worldData.selectedItem}
                           action={ "Use" }
                           onClick={useSelectedItem}/>);
  }
  
  return (
    <Container>
     <Row>
        <Col xs={6}>
          <Stack>
            <ElementImages element={worldData.site}/>
            <Alert className="m-3">
              { statusMessage }
            </Alert>
          </Stack>
        </Col>
        <Col xs={6} style={{ textAlign: "left" }}>
          <Stack>
            <h2>{worldData.site.name}</h2>
            <h5>{worldData.site.description}</h5>
            <PlayerStats charStats={worldStatus.player.status}/>
            { item_card }
          </Stack>
        </Col>
      </Row>
      <Row className="mb-2">
        <Stack direction="horizontal">
          { getSiteCharacters(worldData.site, engageCharacter) }
          { getSiteItems(worldData.site, useItem, takeItem) }
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


function Navigation({ world, setWorldId, worldStatus, reloadWorldStatus, onClose, setView}) {
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
    resetWorldState(world.id)
    reloadWorldStatus();
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
        <Navbar.Text>{getTimeString(worldStatus.current_time)}</Navbar.Text>
        <Navbar.Text class="win_text"> { worldStatus.game_won ? "WIN" : "" }</Navbar.Text>
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
  }, []);
  
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
  }, []);

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
  }, []);

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
  }, []);

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
  } else  if (view === "win") {
     return (
      <div>
	    <CloseBar title="Game Won" onClose={onClose}/>
      <Alert key="success" variant="success">
        Game won: All objectives achived.
      </Alert>
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
  const [worldData, setWorldData] = useState({ world: null,
                                               siteList: null,
                                               site: null,
                                               characterList: null,
                                               character: null,
                                               selectedItem: null,
                                               });
  const [worldStatus, setWorldStatus] = useState(null)
  const [view, setView] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        // Get the details of the world  and a list of sites.

        let calls = Promise.all([ 
          getSiteInstancesList(worldId),
          getWorld(worldId),
          getWorldStatus(worldId)]);
        let [sites, world, world_status] = await calls;

        if (!ignore) {
          let newWorldData = { ...worldData}
          newWorldData.world = world;
          newWorldData.siteList = sites;
          setWorldData(newWorldData);
          setWorldStatus(world_status);
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
  },  []);

  if (worldStatus != null) {
    if (checkSiteLoad()) {
      loadSite(worldData.world.id, worldStatus.location_id);
    } else if (checkCharacterLoad()) {
      loadCharacter(worldData.world.id, worldStatus.engaged_character_id);
    } else if (checkSelectedItemLoad()) {
      loadSelectedItem(worldData.world.id, worldStatus.player.selected_item);
    }
  }

  function updateWorldStatus(newWorldStatus) {
    if (newWorldStatus.game_won && !worldStatus.game_won) {
      setView("win");
    }
    setWorldStatus(newWorldStatus);
  }

  async function reloadWorldStatus() {
    const values = await getWorldStatus(worldId);
    updateWorldStatus(values);
    clearDataCache()
  }

  function checkSiteLoad() {
    if (worldData.site !== null && worldData.site.valid) {
      return (worldStatus.location_id !== worldData.site.id);
    }
    return !(worldStatus.location_id == "" && worldData.site == null);
  }

  function checkCharacterLoad() {
    if (worldData.character !== null && worldData.character.valid) {
      return (worldStatus.engaged_character_id !== worldData.character.id);
    }
    return !(worldStatus.engaged_character_id == "" && worldData.character == null);
  }

  function checkSelectedItemLoad() {
    if (worldData.selectedItem !== null && worldData.selectedItem.valid) {
      return (worldStatus.player.selected_item !== worldData.selectedItem.id)
    }
    return !(worldStatus.player.selected_item == "" && worldData.selectedItem == null);
  }

  async function loadSite(world_id, site_id) {
    let newWorldData = { ...worldData};
    if (site_id === "") {
      newWorldData.site = null;
      setWorldData(newWorldData);
    } else {
      newWorldData.site = await getSiteInstance(world_id, site_id); 
      newWorldData.site.valid = true;
      setWorldData(newWorldData);
    }
  }

  async function loadCharacter(world_id, char_id) {
    let newWorldData = { ...worldData};
    if (char_id  == "") {
      newWorldData.character = null;
      setWorldData(newWorldData);
    } else {
      let calls = Promise.all([ getCharacter(world_id, char_id),
                                getCharacterData(world_id, char_id)]);
        const [character, characterData] = await calls;
 
      newWorldData.character = character
      newWorldData.character.valid = true;
      newWorldData.characterData = characterData
      setWorldData(newWorldData);
    }
  }

  async function loadSelectedItem(world_id, selected_item_id) {
    try {    
      let newWorldData = { ...worldData};
      if (selected_item_id === "") {
        newWorldData.selectedItem = null
        setWorldData(newWorldData);
      } else {
        newWorldData.selectedItem = await getItemInstance(world_id, selected_item_id);
        newWorldData.selectedItem.valid = true;
        setWorldData(newWorldData);
      }
    } 
    catch (e) {
      console.log(e);
    }
  }

  function clearDataCache() {
    let newWorldData = { ...worldData};
    if (newWorldData.site !== null) {
      newWorldData.site.valid = false;
    }
    if (newWorldData.character !== null) {
      newWorldData.character.valid = false;
    }
    if (newWorldData.selectedItem !== null) {
      newWorldData.selectedItem.valid = false;
    }
    setWorldData(newWorldData);
  }

  async function goToSite(site_id) {
    try {    
      let response = await postGoTo(worldData.world.id, site_id);
      setStatusMessage(response.world_status.response_message);    
      updateWorldStatus(response.world_status);
    } catch (e) {
      console.log(e);
    }
  }

  async function selectItem(item_id) {
    try {
      let response = await postSelectItem(worldData.world.id, item_id);
      setStatusMessage(response.world_status.response_message)
      updateWorldStatus(response.world_status);
      if (response.world_status.changed) {
        clearDataCache();
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  function clearView() {
    setView("");
  }

  function clearSite() {
    goToSite("");
    setStatusMessage("");
  }

  async function disengageCharacter() {
    try {    
      const response = await postEngage(worldData.world.id, null);
      updateWorldStatus(response.world_status);
      setStatusMessage("");      
    } catch (e) {
      console.log(e);
    }
  }

  async function siteDropItem(item_id) {
    try {
      let response = await postDropItem(worldData.world.id, item_id, worldStatus.engaged_character_id);
      updateWorldStatus(response.world_status);
      setStatusMessage(response.world_status.response_message);
      if (response.world_status.changed) {
        clearDataCache();
      }
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  // Wait until data loads
  if (worldData.world === null || worldData.siteList === null) {
    return (<div></div>);
  }

  if (view) {
    if (worldData.character !== null) {
    return (<DetailsView view={view}
                         world={worldData.world}
                         selectItem={selectItem}
                         dropItem={siteDropItem}
                         onClose={clearView}/>);
    } else if (worldData.site !== null) {
    return (<DetailsView view={view}
                         world={worldData.world}
                         selectItem={selectItem}
                         dropItem={siteDropItem}
                         onClose={clearView}/>);
    }
    return (<DetailsView view={view}
                         world={worldData.world}
                         selectItem={selectItem}
                         onClose={clearView}/>);
  }

  // Show the character view
  if (worldData.character !== null) {
    return (
     <Container>
       <Row>
        <Navigation worldStatus={worldStatus}
                    world={worldData.world}
                    setWorldId={setWorldId}
                    reloadWorldStatus={reloadWorldStatus}
                    onClose={disengageCharacter}
                    setView={setView}/>
      </Row>
      <Row> 
        <ChatCharacter worldData={worldData}
                       worldStatus={worldStatus}
                       setWorldStatus={updateWorldStatus}
                       clearDataCache={clearDataCache}
                       statusMessage={statusMessage}
                       setStatusMessage={setStatusMessage}/>
        </Row>
      </Container>
    );
  }

  // Show a specific site
  if (worldData.site !== null) {
    return (
      <Container>
       <Row>
        <Navigation worldStatus={worldStatus}
                    world={worldData.world}
                    setWorldId={setWorldId}
                    reloadWorldStatus={reloadWorldStatus}
                    onClose={clearSite}
                    setView={ setView }/>
      </Row>
       <Row> 
        <Site worldData={worldData}
                  worldStatus={worldStatus}
                  setWorldStatus={updateWorldStatus}
                  setWorldState={setWorldData}
                  clearDataCache={clearDataCache}
                  statusMessage={statusMessage}
                  setStatusMessage={setStatusMessage}
                  onClose={clearSite}/>
      </Row>
      </Container>);
  }

  // Show world view
  // Show sites
  return (
    <Container>
      <Row>
        <Navigation worldStatus={worldStatus}
                    world={worldData.world}
                    setWorldId={setWorldId}
                    reloadWorldStatus={reloadWorldStatus}
                    setView={ setView }/>
      </Row>
      <Row >
        <Col xs={6}>
          <Stack>
            <ElementImages element={worldData.world}/>
            <Alert className="m-3">
              { statusMessage }
            </Alert>
          </Stack>
        </Col>
        <Col xs={6} style={{ textAlign: "left" }}>
          <h2>{worldData.world.name}</h2>
          <h5>{worldData.world.description}</h5>
        </Col>                        
      </Row>
      <Row>
        <WorldSites siteList={worldData.siteList} onClick={goToSite}/>
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


function PlayClient() {
  const [worldId, setWorldId] = useState(null);
  useEffect(() => {
    let ignore = false;

    async function getData() {
      // Get initial load data
      try {
        const response = await fetch(get_url("/initdata"),
                                      { headers: headers_get() });
        const values = await response.json();
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

