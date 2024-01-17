import { get_url, headers_get, headers_post } from './util.js';
import { ElementImages, WorldItem, CloseBar } from './common.jsx';
import { getWorldList, getWorld } from './api.js';
import { getSiteList, getItemList, getCharacterList } from './api.js';
import { getSite, getCharacter } from './api.js';

import ChatScreen from './ChatScreen.jsx';

import { useState } from 'react'
import { useEffect } from 'react';

import './App.css'

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



function CharacterScreen({ character }) {
  return (
    <Stack style={{ textAlign: "left" }}>
      <h3>{character.name}</h3>
      <ElementImages element={character}/>
      <h4>Notes:</h4>
      <h5>{character.description}</h5>
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



function ChatCharacter({ worldId, characterId, onClose, onChange}) {
  const [character, setCharacter] = useState(null);
  const [context, setContext ] = useState(
    {
      "worldId": worldId,
      "characterId": characterId
    });  
  const [refresh, setRefresh] = useState(null);    
  useEffect(() => {
    let ignore = false;
    async function getData() {
      // Load the character
      try {
        const value = await getCharacter(worldId, characterId);
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
  }, [worldId, characterId, refresh]);


  function handleUpdate() {
    setRefresh(refresh + 1);
    onChange()
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
                      context={context}
                      getChats={getCharacterChats}
                      postChat={postCharacterChat}
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

function Site({ world, siteId, onClose }) {
  const [site, setSite] = useState(null);
  const [view, setView] = useState(null);
  const [characterId, setCharacterId] = useState(null);
  const [refresh, setRefresh] = useState(null);
  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      // Load the site
      try {
        const value = await getSite(world.id, siteId)
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
  }, [world, siteId, refresh]);

  async function takeItem(item_id) {
    try {
      await postTakeItem(world.id, item_id);
      handleUpdate()
    } catch (e) {
      // TODO: fix reporting
      console.log(e);      
    }
  }

  function handleUpdate() {
    setRefresh(refresh + 1);
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
                     onClose={clearCharacterId}
                     onChange={handleUpdate}/>
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
            <ElementImages element={site}/>
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



async function postGoTo(worldId, siteId) {
  const url = `/worlds/${worldId}/command`;
  const data = { "name": "go",
                 "to": siteId }
  let result = await fetch(get_url(url), {
    method: 'POST',
    body: JSON.stringify(data),
    headers: headers_post()        
  });
  return result;
}

function World({ worldId, setWorldId }) {
  const [world, setWorld] = useState(null);            
  const [siteList, setSiteList] = useState([]);
  const [siteId, setSiteId] = useState(null);
  const [view, setView] = useState(null);

  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        // Get the details of the world  and a list of sites.

        let calls = Promise.all([ getSiteList(worldId),
                                  getWorld(worldId) ]);
        let [sites, world] = await calls;

        if (!ignore) {
          setWorld(world);
          setSiteList(sites);
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

