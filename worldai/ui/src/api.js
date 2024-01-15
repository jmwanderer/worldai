import { get_url, headers_get, headers_post } from './util.js';

async function getWorldList() {
  // Get the list of worlds
  const response =
        await fetch(get_url("/worlds"),
                    { headers: headers_get() });
  const values = await response.json();
  return values;
}


async function getWorld(worldId) {
  const url = `/worlds/${worldId}`;
  const response =
        await fetch(get_url(url),
                    { headers: headers_get() });
  const values = await response.json();
  return values;
}


async function getSiteList(worldId) {
  const url = `/worlds/${worldId}/sites`;
  const response = await fetch(get_url(url),
                               { headers: headers_get() });
  const values = await response.json();
  return values;
}

async function getItemList(worldId) {
  const url = `/worlds/${worldId}/items`;
  const response = await fetch(get_url(url),
                               { headers: headers_get() });                     
  const values = await response.json();
  return values;
}

async function getCharacterList(worldId) {
  const url = `/worlds/${worldId}/characters`;
  const response = await fetch(get_url(url),
                               { headers: headers_get() });                     
  const values = await response.json();
  return values;
}


export { getWorldList, getWorld, getSiteList, getItemList, getCharacterList };
