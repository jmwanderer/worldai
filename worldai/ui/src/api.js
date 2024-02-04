import { get_url, headers_get, headers_post } from './util.js';

async function getCharacter(worldId, characterId) {
  const url = `/worlds/${worldId}/characters/${characterId}`;
  const response = await fetch(get_url(url),
                               { headers: headers_get() });                       const value = await response.json();
  return value
}

async function getSite(worldId, siteId) {
  const url = `/worlds/${worldId}/sites/${siteId}`;
  const response =
        await fetch(get_url(url),
                    { headers: headers_get() });
  const value = await response.json();
  return value;
}

async function getSiteInstance(worldId, siteId) {
  const url = `/worlds/${worldId}/sites/${siteId}/instance`;
  const response =
        await fetch(get_url(url),
                    { headers: headers_get() });
  const value = await response.json();
  return value;
}

async function getItem(worldId, itemId) {
  const url = `/worlds/${worldId}/items/${itemId}`;
  const response =
        await fetch(get_url(url),
                    { headers: headers_get() });
  const value = await response.json();
  return value;
}

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

async function getPlayerData(worldId) {
  const url = `/worlds/${worldId}/player`;
  const response =
        await fetch(get_url(url),
                    { headers: headers_get() });
  const values = await response.json();
  return values;
}

async function getCharacterData(worldId, characterId) {
  const url = `/worlds/${worldId}/characters/${characterId}/instance`;
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

async function getSiteInstancesList(worldId) {
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

async function getCharacterInstancesList(worldId) {
  const url = `/worlds/${worldId}/characters/instances`;
  const response = await fetch(get_url(url),
                               { headers: headers_get() });                     
  const values = await response.json();
  return values;
}


export { getWorldList, getWorld, getSiteList, getItemList, getCharacterList };
export { getCharacterInstancesList, getSiteInstancesList };
export { getCharacter, getSite, getItem, getPlayerData };
export { getCharacterData, getSiteInstance };
