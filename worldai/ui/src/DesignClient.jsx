import { get_url, headers_get, headers_post } from './util.js';
import { getWorldList, getWorld } from './api.js';
import {  getSiteList, getItemList, getCharacterList } from './api.js';
import {  getCharacter, getSite, getItem } from './api.js';
import { ElementImages, WorldItem } from './common.jsx';

import ChatScreen from './ChatScreen.jsx';
import './App.css'

import { useState } from 'react'
import { useEffect } from 'react';

import Button from 'react-bootstrap/Button';
import CloseButton from 'react-bootstrap/CloseButton';
import Card from 'react-bootstrap/Card';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Image from 'react-bootstrap/Image';
import Stack from 'react-bootstrap/Stack';
import Carousel from 'react-bootstrap/Carousel';

function Site({ tag }) {
  const [site, setSite] = useState(null);
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        const site = await getSite(tag.wid, tag.id);
        
        if (!ignore) {
          setSite(site);
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
  }, [tag]);

  if (site === null) {
    return (<></>);
  }

  return (<Stack>
            <Stack direction="horizontal" gap={3}
                   className="align-items-start m-3">
              <ElementImages element={site}/>
              <Container >
                <h2>{site.name}</h2>
                <h5>{site.description}</h5>
              </Container>
            </Stack>
            <h2>Details:</h2>
            { site.details }
          </Stack>);
}


function Item({ tag }) {
  const [item, setItem] = useState(null);
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        const item = await getItem(tag.wid, tag.id);
        
        if (!ignore) {
          setItem(item)
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
  }, [tag]);

  if (item === null) {
    return (<></>);
  }

  return (<Stack>
            <Stack direction="horizontal" gap={3}
                   className="align-items-start m-3">
              <ElementImages item={item}/>
              <Container >
                <h2>{item.name}</h2>
                <h5>{item.description}</h5>
              </Container>
            </Stack>
            <h2>Details:</h2>
            { item.details }
          </Stack>);
}

function Character({ tag }) {
  const [character, setCharacter] = useState(null);
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        const character = await getCharacter(tag.wid, tag.id);
        
        if (!ignore) {
          setCharacter(character);
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
  }, [tag]);

  if (character === null) {
    return (<></>);
  }

  return (<Stack>
            <Stack direction="horizontal" gap={3}
                   className="align-items-start m-3">
              <ElementImages element={character}/>
              <Container >
                <h2>{character.name}</h2>
                <h5>{character.description}</h5>
              </Container>
            </Stack>
            <h2>Details:</h2>
            { character.details }

            <h2>Personality:</h2>
            { character.personality }
          </Stack>);
}


function World({ tag }) {
  const [world, setWorld] = useState(null);
  const [characters, setCharacters] = useState(null);
  const [items, setItems] = useState(null);
  const [sites, setSites] = useState(null);    
  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        // Get the details of the world  and a list of sites.

        let calls = Promise.all([ getWorld(tag.wid),
                                  getSiteList(tag.wid),
                                  getItemList(tag.wid),
                                  getCharacterList(tag.wid) ]);
        let [world, sites, items, characters ] = await calls;
        
        if (!ignore) {
          setWorld(world);
          setSites(sites);
          setItems(items);          
          setCharacters(characters);
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
  }, [tag]);

  if (world !== null) {
    const character_list = characters.map(entry =>
      <li key={entry.id}> <b>{entry.name}</b> - {entry.description} </li>
    );
    const item_list = items.map(entry =>
      <li key={entry.id}> <b>{entry.name}</b> - {entry.description} </li>
    );
    const site_list = sites.map(entry =>
      <li key={entry.id}> <b>{entry.name}</b> - {entry.description} </li>
    );

    
    return (
      <Stack>
        <Stack direction="horizontal" gap={3} className="align-items-start m-3">
          <ElementImages element={world}/>
          <Container >
            <h2>{world.name}</h2>
            <h5>{world.description}</h5>
          </Container>
        </Stack>
        <h2>Details:</h2>
        { world.details }

        <h2>Main Characters:</h2>
        <ul>
          { character_list }
        </ul>

        <h2>Key Sites:</h2>
        <ul>
          { site_list }
        </ul>
        
        <h2>Significant Items:</h2>
        <ul>
          { item_list }
        </ul>

      </Stack>
    );
  } else {
    return (<></>);
  }
}

function WorldList() {
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

  const entries = worldList.map(entry =>
    <WorldItem key={entry.id} world={entry}/>
  );

  return (
    <Stack className="mt-3">
      { entries }
    </Stack>
  );
}
  

function DesignView({chatView}) {
  const [viewContent, setViewContent] = useState(null);  

  let type = 'None';
  if (chatView !== null &&
      Object.hasOwn(chatView, 'element_type')) {
    type = chatView.element_type;
  }
  let content = "";
  if (type === 'None') {
    content = ( <WorldList/> );
  } else if (type === 'World') {
    content = ( <World tag={chatView}/> );    
  } else if (type === 'Character') {
    content = ( <Character tag={chatView}/> );        
  } else if (type === 'Site') {
    content = ( <Site tag={chatView}/> );            
  } else if (type === 'Item') {
    content = ( <Item tag={chatView}/> );     
  }
  
  return ( <div style={{ overflow: "auto",
                       maxHeight: "90vh" }}>
             { content }
           </div> );
}



function DesignChat({name, setChatView}) {

  async function getDesignChats(context) {
    const url = '/design_chat'  
    const response =
          await fetch(get_url(url),
                      { headers: headers_get() });
    const values = await response.json();
    setChatView(values.view);
    return values;
  }

  async function postDesignChat(context, user_msg) {
    const data = { "user": user_msg }
    const url = '/design_chat'    
    // Post the user request
    const response = await fetch(get_url(url), {
      method: 'POST',
      body: JSON.stringify(data),
      headers: headers_post()
    });
    const values = await response.json();
    setChatView(values.view);    
    return values;
  }

  async function clearDesignChat(context) {
    const url = '/design_chat'    
    const response = await fetch(get_url(url), {
      method: 'POST',
      body: '{ "command": "clear_thread" }',       
      headers: headers_post()
    });
  }


  function handleUpdate() {
  }

  return ( <div style={{ height: "100%", maxHeight: "90vh" }}>
             <ChatScreen name={name}
                         context={"dummy"}
                         getChats={getDesignChats}
                         postChat={postDesignChat}
                         clearChat={clearDesignChat}
                         onChange={handleUpdate}/>
           </div> );
}


function DesignClient() {
  const [chatView, setChatView] = useState(null);
  
  return (
    <Container fluid>
      <Row>
        <Col xs={4}>
          <DesignChat name={"Assistant"}
                      setChatView={setChatView}/>
        </Col>
        <Col xs={8}>
          <DesignView chatView={chatView}/>          
        </Col>
      </Row>
    </Container>
  );
}
    
export default DesignClient;
