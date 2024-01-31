import { get_url, headers_get, headers_post } from './util.js';

import { useState } from 'react'
import { useRef } from 'react';
import { useEffect } from 'react';
import { forwardRef } from 'react';
import { useImperativeHandle } from 'react';
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
  let event_message = "";
  let reply_message = "";        

  if (message.user.length > 0) {
    user_message = (
      <div className="App-message">            
        <b>You:</b> <br/> { message.user } <br/>
      </div>);
  }
  if (message.updates && message.updates.length > 0) {
    updates_message = (
      <div className="App-message">            
        <i>{ message.updates }</i>
      </div>);
  }
  if (message.event && message.event.length > 0) {
    event_message = (
      <div className="App-message">            
        <i>{ message.event }</i>
      </div>);
  }
  if (message.reply && message.reply.length > 0) {
    reply_message = (
      <div className="App-message">
        <b> {name}: </b>
          <Markdown>
              { message.reply}
          </Markdown>
      </div>
    )
  }
  return (
    <div>
      { user_message }
      { event_message }
      { updates_message }
      { reply_message }
    </div>
  );
}

const CurrentMessage = forwardRef(({ content, chatState }, msgRef) => {
  // Use a forwardRef to expose a component div to parents in order to
  // scoll into view.
  
  let user = "";
  if (content.user.length > 0) {
    user = <div className="App-message">
             <b>You:</b> <br/> { content.user } <br/>             
           </div>;
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
    <textarea className="m-2" style={{ minHeight: "2em" }}
              value={value} 
              disabled={disabled}
              onChange={onChange} onKeyDown={onKeyDown}/>
  );
}


const ChatScreen = forwardRef(({ name, calls,
                                 chatEnabled, onChange, onChatDone},
                               submitActionRef) =>
{
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
        setChatState("waiting");                
        const values = await calls.getChats(calls.context);
        if (!ignore) {
          setChatHistory(values["messages"]);
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
  }, []);

  function chatDone() {
    if (typeof onChatDone !== 'undefined') {
      onChatDone();
    }
  }

  if (typeof submitActionRef !== 'undefined') {
    useImperativeHandle(submitActionRef, (item_id, character_id) => ({
      submitAction: (item_id, character_id) => {
        runChatAction(item_id, character_id);
      }}))
  }

  function processChatMessage(values) {
    // Append to history that is displayed
    setChatHistory([...chatHistory, values])
    // Clear the current message
    setCurrentMessage({user: "", error: "" });
    console.log("enabled: " + values["enabled"]);
        
    if (values["enabled"]) {
      setChatState("ready");
    } else {
      setChatState("disabled");            
    }
    if (values["updates"].length > 0) {
      // Server signaled a change in state.
      onChange();
    }
  }
  
  async function runChatAction() {
    if (!chatEnabled) {
      return
    }

    // Post a user action for the character        
    setCurrentMessage({user: "", error: ""});
    setChatState("waiting");

    try {
      const values = await calls.postChatAction(calls.context);
      processChatMessage(values);
    } catch (e) {
      console.log(e);
      setCurrentMessage({error: "Something went wrong."});
      setChatState("ready")
    }
    // Signal chat was completed
    chatDone();
    // TODO - return a result
  }
                                    
  function submitClick() {
    let user_msg = userInput
    setCurrentMessage({user: user_msg, error: ""});
    setUserInput("");
    setChatState("waiting");

    async function getData() {
      // Post the user request
      try {
        // Get response
        const values = await calls.postChat(calls.context, user_msg);
        processChatMessage(values);
      } catch (e) {
        console.log(e);
        setCurrentMessage({user: user_msg,
                           error: "Something went wrong."});
        setChatState("ready")
      }
      // Signal chat was completed
      chatDone();
    }
    getData();
  }

  function submitClear() {
    try {
      setChatState("disabled");      
      calls.clearChat(calls.context);
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


  let disabled = (chatState !== "ready") || !chatEnabled;
  let text_disabled = (chatState === "disabled") || !chatEnabled;
  
  let clearButton = ""
  if (calls.clearChat !== null) {
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
});

export default ChatScreen;
