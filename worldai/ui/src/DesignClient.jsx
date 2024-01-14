import { get_url, headers_get, headers_post } from './common.js';
import { getWorldList, getWorld } from './api.js';
import { WorldImages } from './common.jsx';

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
  return (<></>);
}

function Item({ tag }) {
  return (<></>);
}

function Character({ tag }) {
  return (<></>);
}


function World({ tag }) {
  const [world, setWorld] = useState(null);            
  
  useEffect(() => {
    let ignore = false;

    async function getData() {
      try {
        // Get the details of the world  and a list of sites.

        let value = await getWorld(tag.wid);

        if (!ignore) {
          setWorld(value);
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
    return (
      <Container>
        <Row >
          <Col xs={6}>
            <WorldImages world={world}/>
          </Col>
          
          <Col xs={6} style={{ textAlign: "left" }}>
            <h2>{world.name}</h2>
            <h5>{world.description}</h5>
          </Col>                        
        </Row>
      </Container>            
    );
  } else {
    return (<></>);
  }
}

function WorldItem({ world }) {

  return (
    <div className="card mb-3 container">
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
    <Container>
      <Row>
        <Col xs={6}>
          <DesignChat name={"Assistant"}
                      setChatView={setChatView}/>
        </Col>
        <Col xs={6}>
          <DesignView chatView={chatView}/>          
        </Col>
      </Row>
    </Container>
  );
}
    
export default DesignClient;
