//import { meta.env } from 'vite';


function extract_prefix(url) {
  // https://localhost:3000/  --> https://localhost:3000
  // https://localhost:3000/ui/play --> https://localhost:3000
  // https://localhost:3000/worldai/ui/play --> https://localhost:3000/worldai

  // Find 3rd / character
  let i = url.indexOf('/');
  i = url.indexOf('/', i + 1)
  i = url.indexOf('/', i + 1)

  // Find 2nd to last / character
  let end = url.lastIndexOf('/')
  end = url.lastIndexOf('/', end - 1)

  if (end < i) {
    end = i;
  } 
  return url.substr(0, end);
}

// global URL, auth_key
let URL= extract_prefix(document.location.href);
console.log("URL Prefix: " + URL);

// get from global variable set in index.html
// For npm run dev sessions, set VITE_AUTH_KEY in the environment
// Following comment is required for compile.
/* global auth_key */
let AUTH_KEY="auth"
if (typeof auth_key !== 'undefined' && auth_key.substring(0,2) !== "{{") {
  AUTH_KEY=auth_key
} else {
  AUTH_KEY=import.meta.env.VITE_AUTH_KEY;
}
console.log("AUTH Key: " + AUTH_KEY);


function get_url(suffix) {
  return URL + '/api'+ suffix;
}

function headers_get() {
  return {  "Authorization": "Bearer " + AUTH_KEY };
}

function headers_post() {
  return {
    'Content-Type': 'application/json',    
    "Authorization": "Bearer " + AUTH_KEY
  };
}


export { get_url, headers_get, headers_post  };

