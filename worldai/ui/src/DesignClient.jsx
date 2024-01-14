import { get_url, headers_get, headers_post } from './common.js';
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

async function getChatViewContent(view) {
  const response =
        await fetch(get_url("/view_props"), {
          method: 'POST',
          body: JSON.stringify(view),
          headers: headers_post()
        });
  const value = await response.json();
  return value; 
}

function DesignView({chatView}) {
  const [viewContent, setViewContent] = useState(null);  
  useEffect(() => {
    let ignore = false;
    async function getData() {
      // TODO: replace this scheme.
      try {
        if (chatView !== null) {
          const value = await getChatViewContent(chatView);
          if (!ignore) {
            setViewContent(value)
          }
        }
      } catch (e) {
        console.log(e);
      }
    }

    getData();
    return () => {
      ignore = true;
    }
  }, [chatView]);
  
  return ( <div style={{ overflow: "auto",
                       maxHeight: "90vh" }}>
             { (viewContent === null) ? "" : viewContent.html }
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
