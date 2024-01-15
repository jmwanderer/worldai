import { get_url, headers_get, headers_post } from './util.js';

import { useState } from 'react'
import { useRef } from 'react';
import { useEffect } from 'react';
import { forwardRef } from 'react';
import Markdown from 'react-markdown';

import './App.css'

import Button from 'react-bootstrap/Button';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Stack from 'react-bootstrap/Stack';

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
          <Markdown>
              { message.reply}
          </Markdown>
      </div>
      { updates_message }
    </div>
  );
}

const CurrentMessage = forwardRef(({ content, chatState }, msgRef) => {
  // Use a forwardRef to expose a component div to parents in order to
  // scoll into view.
  
  let user = "";
  if (content.user.length > 0) {
    user = <div> User: {content.user} </div>;
  }
  let running = "";
  if (chatState === "waiting") {
    running = <div className="App-running"><i> Running... </i></div>
  }
  let error = "";
  if (content.error.length > 0) {
    error = <div> Error: { content.error } </div>;
  }
  return (
    <div className="p-2" ref={msgRef}>
      { user }
      { running}
      { error }
    </div>
  );
});

function MessageScreen({chatHistory, currentMessage, chatState, name}) {
  const msgRef = useRef(null);
  useEffect(() => {
    const {current} = msgRef;
    if (current !== null) {
      current.scrollIntoView({behavior: "smooth"});
    }
  }, [chatHistory, currentMessage]);
  
  const entries = chatHistory.map(entry =>
    <MessageExchange key={entry.id} message={entry} name={name}/>
  );

  return (
    <Stack className="border m-2" style={{ textAlign: "left",
                                           overflow: "auto"}}>
      
      { entries }
      
      <CurrentMessage content={currentMessage}
                      chatState={chatState}
                      ref={msgRef}/>
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


function ChatScreen({ name, context, getChats, postChat, clearChat, onChange}) {
  const [chatHistory, setChatHistory] = useState([]);
  const [currentMessage,
         setCurrentMessage] = useState({ user: "", error: ""});
  const [userInput, setUserInput] = useState("")
  const [chatState, setChatState] = useState("ready")

  useEffect(() => {
    let ignore = false;    

    async function getData() {
      // Get the chat history.
      try {
        const values = await getChats(context);
        if (!ignore) {
          setChatHistory(values["messages"]);
          if (values["messages"].length === 0) {
            setChatState("waiting");                
            const values = await postChat(context, "");
            setChatHistory(c => [...c, values])
          }
          if (values["enabled"]) {
            setChatState("ready");
          } else {
            setChatState("disabled");
          }
        }
      } catch (e) {
        console.log(e);
        setCurrentMessage({user: "",
                           error: "Something went wrong."});
        setChatState("ready")        
      }
    }
    
    getData();
    return () => {
      ignore = true;
    }
  }, [ context ]);

  function submitClick() {
    let user_msg = userInput
    setCurrentMessage({user: user_msg, error: ""});
    setUserInput("");
    setChatState("waiting");

    async function getData() {
      // Post the user request
      try {            
        const values = await postChat(context, user_msg);
        setChatHistory([...chatHistory, values])
        setCurrentMessage({user: "", error: "" });
        if (values["enabled"]) {
          setChatState("ready");
        } else {
          setChatState("disabled");            
        }
      } catch (e) {
        console.log(e);
        setCurrentMessage({user: user_msg,
                           error: "Something went wrong."});
        setChatState("ready")
      }
      onChange()
    }
    getData();
  }

  function submitClear() {
    try {
      setChatState("disabled");      
      clearChat(context);
      setChatHistory([]);
      setChatState("ready")      
    } catch (e) {
      console.log(e);
    }
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
  let text_disabled = (chatState === "disabled");
  
  let clearButton = ""
  if (typeof clearChat !== 'undefined') {
    clearButton = (
      <Col>
        <Button disabled={disabled}
                onClick={submitClear}
                text="Clear Thread">
          ClearThread
        </Button>
      </Col>
    );
  }

  return (
    <Stack style={{ height: "100%", maxHeight: "90vh" }}>
      <MessageScreen chatHistory={chatHistory}
                     currentMessage={currentMessage}
                     chatState={chatState}
                     name={name}/>
      <UserInput value={userInput}
                 onChange={handleInputChange}
                 onKeyDown={handleKeyDown}
                 disabled={text_disabled}/>
      <Container style={{ textAlign: "center" }}>
        <Row>
          { clearButton }
          <Col>
            <Button disabled={disabled}
                    onClick={submitClick}
                    text="Submit">
              Submit
            </Button>
          </Col>
        </Row>
      </Container>
    </Stack>
  );
}

export default ChatScreen;
