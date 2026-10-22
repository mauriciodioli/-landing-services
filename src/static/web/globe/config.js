// Coordinates supplied for DPIA locations. The fifth entry stays disabled until defined.
export const CITIES = [
  {id:'cordoba',name:'Córdoba',country:{es:'Argentina',en:'Argentina',it:'Argentina'},lat:-31.42,lon:-64.18,enabled:true},
  {id:'guadalajara',name:'Guadalajara',country:{es:'México',en:'Mexico',it:'Messico'},lat:20.67,lon:-103.35,enabled:true},
  {id:'copenhagen',name:'Copenhague',names:{en:'Copenhagen',it:'Copenaghen'},country:{es:'Dinamarca',en:'Denmark',it:'Danimarca'},lat:55.68,lon:12.57,enabled:true},
  {id:'wroclaw',name:'Wrocław',country:{es:'Polonia',en:'Poland',it:'Polonia'},lat:51.11,lon:17.04,enabled:true},
  {id:'future',name:'',country:{es:'',en:'',it:''},lat:null,lon:null,enabled:false},
];
export const SETTINGS = {
  rotationSpeed:0.045, // radians per second
  initialRotation:-0.9, initialTilt:0.22,
  starColor:'#ffe3a0', atmosphereColor:'#45bce8',
  maxPixelRatio:1.75, mobilePixelRatio:1.25,
};
export const activeCities = () => CITIES.filter(c => c.enabled && Number.isFinite(c.lat) && Number.isFinite(c.lon) && Math.abs(c.lat)<=90 && Math.abs(c.lon)<=180);
export const cityLabel = (city,lang) => `${city.names?.[lang] || city.name}, ${city.country[lang] || city.country.es}`;
