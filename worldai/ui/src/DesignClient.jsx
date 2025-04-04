//
// React client for design app
//
//    Jim Wanderer
//    http://github.com/jmwanderer
//

import { get_url, headers_get, headers_post } from './util.js';
import { getWorldList, getWorld  } from './api.js';
import {  getSiteList, getItemList, getCharacterList } from './api.js';
import {  getCharacter, getSite, getItem } from './api.js';
import { getDocumentList, getDocument } from './api.js';
import { ElementImages, WorldItem, CloseBar } from './common.jsx';

import ChatScreen from './ChatScreen.jsx';
import './App.css'

import { useState } from 'react'
import { useEffect } from 'react';

import Markdown from 'react-markdown';
import Button from 'react-bootstrap/Button';
import CloseButton from 'react-bootstrap/CloseButton';
import Card from 'react-bootstrap/Card';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Image from 'react-bootstrap/Image';
import Stack from 'react-bootstrap/Stack';
import Carousel from 'react-bootstrap/Carousel';
import Accordion from 'react-bootstrap/Accordion'
import Table from 'react-bootstrap/Table'

function Site({ tag, setChatView }) {
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

  function changeWorld() {
    setChatView({ "wid": tag.wid,
                  "element_type": "World",
                  "id": tag.wid });
  }

  if (site === null) {
    return (<></>);
  }

  return (<Stack>
            <CloseBar onClose={changeWorld}/>
            <Stack direction="horizontal" gap={3}
                   className="align-items-start m-3">
              <ElementImages element={site}/>
              <Stack>
                <h2>{site.name}</h2>
                <Markdown>
                  {site.description}
                </Markdown>
                <Table>
                 <tbody>
                    <tr>
                      <td style={{whiteSpace: "nowrap"}}>Default Open:</td>
                      <td style={{width: "99%"}}>
                         { site.default_open ? "Yes" : "No" }
                      </td>
                    </tr>
                  </tbody>
                </Table>
              </Stack>
            </Stack>
            <h2>Details:</h2>
            <Markdown>            
              { site.details }
            </Markdown>
          </Stack>);
}


function Document({ tag, setChatView }) {
  const [document, setDocument ] = useState(null);
  useEffect(() => {
    let ignore = false;
    async function getData() {
      try {
        console.log("load doc: " + tag.id);
        const doc = await getDocument(tag.wid, tag.id)
        if (!ignore) {
          setDocument(doc)
        }
      }
      catch (e) {
        console.log(e)
      }
    }

    getData();
    return () => {
      ignore = true;
    }
  }, [tag]);

  function changeWorld() {
    setChatView({ "wid": tag.wid,
                  "element_type": "World",
                  "id": tag.wid });
  }

  if (document === null) {
    return (<></>);
  }
  console.log(document);
  let sections = document.sections.map(entry => 
    <div key={entry.heading}>
      <h5>{entry.heading}</h5>
      <Markdown>
        {entry.text}
      </Markdown>
    </div>
    );

  return (<Stack>
    <CloseBar onClose={changeWorld}/>
    <Stack gap={3}
           className="align-items-start m-3">
        <h2>{document.name}</h2>
        {sections}
    </Stack>
  </Stack>);
  
}


function Item({ tag, setChatView }) {
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

  function changeWorld() {
    setChatView({ "wid": tag.wid,
                  "element_type": "World",
                  "id": tag.wid });
  }

  if (item === null) {
    return (<></>);
  }

  return (<Stack>
    <CloseBar onClose={changeWorld}/>
    <Stack direction="horizontal" gap={3}
           className="align-items-start m-3">
      <ElementImages element={item}/>
      <Container >
        <h2>{item.name}</h2>
        <Markdown>
          {item.description}
        </Markdown>
        <Table>
          <tbody>
            <tr>
              <td>
                Mobile:
              </td>
              <td>
                {item.mobile ? "Yes" : "No" }
              </td>
            </tr>
            <tr>
              <td>
                Ability:
              </td>
              <td>
                {item.ability.effect}
                {item.ability.effect == "open" ? " : "
                                         + item.ability.site : "" }
              </td>
            </tr>
          </tbody>
        </Table>
      </Container>
    </Stack>
    <h2>Details:</h2>
    <Markdown>
      { item.details }
    </Markdown>
  </Stack>);
}

function Character({ tag, setChatView }) {
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

  function changeWorld() {
    setChatView({ "wid": tag.wid,
                  "element_type": "World",
                  "id": tag.wid });
  }

  return (<Stack>
            <CloseBar onClose={changeWorld}/>
            <Stack direction="horizontal" gap={3}
                   className="align-items-start m-3">
              <ElementImages element={character}/>
              <Container >
                <h2>{character.name}</h2>
                <Markdown>
                  {character.description}
                </Markdown>
              </Container>
            </Stack>
            <Accordion>
              <Accordion.Item eventKey='0'>
                <Accordion.Header>
                  Details
                  { character.details.length === 0 ? " -- TBD" : ""}
                </Accordion.Header>
                <Accordion.Body>
                  <Markdown>
                    { character.details }
                  </Markdown>
                </Accordion.Body>
              </Accordion.Item>

              <Accordion.Item eventKey='1'>
                <Accordion.Header>
                  Personality
                  { character.personality.length === 0 ? " -- TBD" : ""}
                </Accordion.Header>
                <Accordion.Body>
                  <Markdown>
                    { character.personality }
                  </Markdown>
                </Accordion.Body>
              </Accordion.Item>

              <Accordion.Item eventKey='2'>
                <Accordion.Header>
                  Physical Appearance
                  { character.appearance.length === 0 ? " -- TBD" : ""}
                </Accordion.Header>
                <Accordion.Body>
                  <Markdown>
                    { character.appearance }
                  </Markdown>
                </Accordion.Body>
              </Accordion.Item>

              <Accordion.Item eventKey='3'>
                <Accordion.Header>
                  Traits
                  { character.traits.length === 0 ? " -- TBD" : ""}
                </Accordion.Header>
                <Accordion.Body>
                  <Markdown>
                    { character.traits }
                  </Markdown>
                </Accordion.Body>
              </Accordion.Item>

              <Accordion.Item eventKey='4'>
                <Accordion.Header>
                  Behavior
                  { character.behavior.length === 0 ? " -- TBD" : ""}
                </Accordion.Header>
                <Accordion.Body>
                  <Markdown>
                    { character.behavior }
                  </Markdown>
                </Accordion.Body>
              </Accordion.Item>

              <Accordion.Item eventKey='5'>
                <Accordion.Header>
                  Relationships
                  { character.relationships.length === 0 ? " -- TBD" : ""}
                </Accordion.Header>
                <Accordion.Body>
                  <Markdown>
                    { character.relationships }
                  </Markdown>
                </Accordion.Body>
              </Accordion.Item>

              <Accordion.Item eventKey='6'>
                <Accordion.Header>
                  Backstory
                  { character.backstory.length === 0 ? " -- TBD" : ""}
                </Accordion.Header>
                <Accordion.Body>
                  <Markdown>
                    { character.backstory }
                  </Markdown>
                </Accordion.Body>
              </Accordion.Item>

            </Accordion>
          </Stack>);
}


function World({ tag, setChatView }) {
  const [world, setWorld] = useState(null);
  const [characters, setCharacters] = useState(null);
  const [items, setItems] = useState(null);
  const [sites, setSites] = useState(null);    
  const [documents, setDocuments] = useState(null);      
  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        // Get the details of the world  and a list of sites.

        let calls = Promise.all([ getWorld(tag.wid),
                                  getSiteList(tag.wid),
                                  getItemList(tag.wid),
                                  getCharacterList(tag.wid),
                                  getDocumentList(tag.wid) ]);
        let [world, sites, items, characters, docs ] = await calls;
        
        if (!ignore) {
          setWorld(world);
          setSites(sites);
          setItems(items);          
          setCharacters(characters);
          setDocuments(docs);
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

  function changeToWorldList() {
    setChatView({ "wid": null,
                  "element_type": "None",
                  "id": null });
  }

  function changeToCharacter(id) {
    setChatView({ "wid": tag.wid,
                  "element_type": "Character",
                  "id": id });
  }

  function changeToSite(id) {
    setChatView({ "wid": tag.wid,
                  "element_type": "Site",
                  "id": id });
  }

  function changeToDocument(id) {
    setChatView({ "wid": tag.wid,
                  "element_type": "Document",
                  "id": id });
  }

  function changeToItem(id) {
    setChatView({ "wid": tag.wid,
                  "element_type": "Item",
                  "id": id });
  }

  function formatDescription(description) {
    if (description.length > 80) {
      let cut = description.indexOf(" ", 65);
      if (cut > 80) {
        cut = 80;
      }
      return description.substring(0, cut) + "...";
    }
    return description;
  }

  if (world !== null) {
    const character_list = characters.map(entry =>
      <li key={entry.id}>
        <b>
          <a className="link-primary link-underline-opacity-100"
             href="#"
             onClick={() => changeToCharacter(entry.id)}>
            {entry.name}
          </a>
        </b>
        - {formatDescription(entry.description)}
      </li>
    );

    const item_list = items.map(entry =>
      <li key={entry.id}>
        <b>
          <a className="link-underline-primary"
             href="#"             
             onClick={() => changeToItem(entry.id)}>
            {entry.name}
          </a>

        </b>
        - {formatDescription(entry.description)} [{entry.ability}]
      </li>

    );

    const site_list = sites.map(entry =>
      <li key={entry.id}>
        <b>
          <a className="link-underline-primary"
             href="#"             
             onClick={() => changeToSite(entry.id)}>
            {entry.name}
          </a>
        </b>
        - {formatDescription(entry.description)}
      </li>

    );

    const doc_list = documents.map(entry =>
      <li key={entry.id}>
        <b>
          <a className="link-underline-primary"
          href="#"
          onClick={() => changeToDocument(entry.id)}>          
            {entry.name}
          </a>
        </b>
      </li>)

    const start_conditions = world.start_conditions.map(entry =>
      <li key={entry}>
        {entry}
      </li>
      );


    const end_goals = world.end_goals.map(entry =>
      <li key={entry}>
        {entry}
      </li>
      );

    
    return (
      <Stack>
        <CloseBar onClose={changeToWorldList}/>        
        <Stack direction="horizontal" gap={3} className="align-items-start m-3">
          <ElementImages element={world}/>
          <Container >
            <h2>{world.name}</h2>
            <Markdown>
              {world.description}
            </Markdown>
          </Container>
        </Stack>
        <Accordion>
          <Accordion.Item eventKey="0">
            <Accordion.Header>
              Details
              { world.details.length === 0 ? " -- TBD" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <Markdown>
                { world.details }
              </Markdown> 
              </Accordion.Body>
          </Accordion.Item>

          <Accordion.Item eventKey='1'>
            <Accordion.Header>
              Main Characters
              { characters.length === 0 ? " -- None" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <ul>
                { character_list }
              </ul>
            </Accordion.Body>
          </Accordion.Item>
 
          <Accordion.Item eventKey='2'>
            <Accordion.Header>
              Key Sites
              { sites.length === 0 ? " -- None" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <ul>
                { site_list }
              </ul>
            </Accordion.Body>
          </Accordion.Item>

          <Accordion.Item eventKey='3'>
            <Accordion.Header>
              Significant Items
              { items.length === 0 ? " -- None" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <ul>
                { item_list }
              </ul>
            </Accordion.Body>
          </Accordion.Item>

          <Accordion.Item eventKey='4'>
            <Accordion.Header>
              Documents
              { documents.length === 0 ? " -- None" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <ul>
                { doc_list }
              </ul>
            </Accordion.Body>
          </Accordion.Item>

          <Accordion.Item eventKey='5'>
            <Accordion.Header>
              Planning Notes:
              { world.plans.length === 0 ? " -- None" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <Markdown>
                { world.plans }          
              </Markdown>
            </Accordion.Body>
          </Accordion.Item>

          <Accordion.Item eventKey='6'>
            <Accordion.Header>
              Starting Conditions
              { start_conditions.length === 0 ? " -- None" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <ul>
                { start_conditions }
              </ul>
            </Accordion.Body>
          </Accordion.Item>
 
          <Accordion.Item eventKey='7'>
            <Accordion.Header>
              End Goals
              { end_goals.length === 0 ? " -- None" : ""}
            </Accordion.Header>
            <Accordion.Body>
              <ul>
                { end_goals }
              </ul>
            </Accordion.Body>
          </Accordion.Item>
        </Accordion>
      </Stack>
    );
  } else {
    return (<></>);
  }
}

function WorldList({ setChatView }) {
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

  function selectWorld(id) {
    setChatView({ "wid": id,
                  "element_type": "World",
                  "id": id });
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
  

function DesignView({chatView, setChatView}) {

  let type = 'None';
  if (chatView !== null &&
      Object.hasOwn(chatView, 'element_type')) {
    type = chatView.element_type;
  }
  let content = "";
  if (type === 'None') {
    content = (<WorldList setChatView={setChatView}/>);
  } else if (type === 'World') {
    content = (<World tag={chatView}
                       setChatView={setChatView}/>);    
  } else if (type === 'Character') {
    content = (<Character tag={chatView} setChatView={setChatView}/>);
  } else if (type === 'Site') {
    content = (<Site tag={chatView} setChatView={setChatView}/>);
  } else if (type === 'Item') {
    content = (<Item tag={chatView} setChatView={setChatView}/>);
  } else if (type === 'Document') {
    content = (<Document tag={chatView} setChatView={setChatView}/>);
  }

  return ( <div style={{ overflow: "auto",
                       maxHeight: "90vh" }}>
             { content }
           </div> );
}



function DesignChat({name, chatView, setChatView}) {

  async function getDesignChats(context) {
    const url = '/design_chat'  
    const response =
          await fetch(get_url(url),
                      { headers: headers_get() });
    const values = await response.json();
    console.log("get view: " + JSON.stringify(values.view));
    // Ignore going to the top view. No need to do that.
    if (values.view.element_type !== "None") {
      setChatView(values.view);
    }
    return values.history_response;
  }

  async function postChatStart(context, user_msg) {
    // Potentially update current view
    console.log("post view: " + JSON.stringify(context));
    // Post message
    const msg_data = {
      "command": "start",
      "user": user_msg,
      "view": context
     }
    const url_msg = '/design_chat'    
    // Post the user request
    console.log("start chat: " + user_msg)
    const response = await fetch(get_url(url_msg), {
      method: 'POST',
      body: JSON.stringify(msg_data),
      headers: headers_post()
    });
    const values = await response.json();
    if (values.chat_response.done) {
      setChatView(values.view); 
    }
    return values.chat_response;
  }

  async function postChatContinue(context, msg_id) {
    // Post message
    const msg_data = {
      "command": "continue",
      "msg_id": msg_id }
    const url_msg = '/design_chat'    

    // Post the user request
    console.log("continue chat: " + msg_id)    
    const response = await fetch(get_url(url_msg), {
      method: 'POST',
      body: JSON.stringify(msg_data),
      headers: headers_post()
    });
    const values = await response.json();
    if (values.chat_response.done) {
      setChatView(values.view); 
    }
    return values.chat_response;
  }

  async function clearDesignChat(context) {
    const url = '/design_chat'    
    const response = await fetch(get_url(url), {
      method: 'POST',
      body: '{ "command": "clear" }',       
      headers: headers_post()
    });
  }



  const calls = {
    context: chatView,
    getChats: getDesignChats,
    postChat: postChatStart,
    continueChat: postChatContinue,
    clearChat: clearDesignChat,
    postChatAction: null
  };
  

  return ( <div style={{ height: "100%", maxHeight: "90vh" }}>
             <ChatScreen name={name}
                         chatEnabled={true}
                         calls={calls}/>
           </div> );
}


function DesignClient() {
  const [chatView, setChatView] = useState(null);
  return (
    <Container fluid>
      <Row>
        <Col xs={4}>
          <DesignChat name={"Assistant"}
                      chatView={chatView}
                      setChatView={setChatView}/>
        </Col>
        <Col xs={8}>
          <DesignView chatView={chatView} setChatView={setChatView}/>          
        </Col>
      </Row>
    </Container>
  );
}
    
export default DesignClient;
